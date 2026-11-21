import logging
import os
import shutil
import time
from collections import deque
from compression import lzma
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .config import (
    RELEASES_DIR,
    STORE_DIR,
    AbortGCError,
    NarUrl,
    StoreHash,
    SyncConfig,
)
from .narinfo import (
    NarInfo,
    NarInfoCache,
    read_narinfo_file,
    read_store_root_hashes,
    scan_store_dir,
)

GC_READ_BATCH_SIZE = 4096
GC_PROGRESS_INTERVAL = 15.0

logger = logging.getLogger(__name__)


def _try_unlink(path: Path) -> bool:
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError as e:
        logger.warning("Failed to delete %s: %r", path, e)
        return False


def _ignore_or_abort_missing(
    store_hash: StoreHash,
    roots: set[StoreHash],
    err: Exception | None = None,
) -> None:
    if store_hash in roots and (err is None or isinstance(err, FileNotFoundError)):
        logger.debug("Missing root narinfo %s; skipping", store_hash)
        return
    detail = f": {err}" if err is not None else ""
    raise AbortGCError(f"Missing or invalid retained narinfo {store_hash}{detail}")


def read_narinfo_batch(
    hashes: list[StoreHash],
    working_dir: Path,
    executor: ThreadPoolExecutor,
) -> list[tuple[StoreHash, NarInfo | None, Exception | None]]:
    def read_one(h: StoreHash) -> tuple[StoreHash, NarInfo | None, Exception | None]:
        try:
            return h, read_narinfo_file(h, working_dir), None
        except (KeyError, OSError, ValueError) as e:
            return h, None, e

    return list(executor.map(read_one, hashes))


def collect_local_closure(
    releases: set[Path],
    present: set[StoreHash],
    cfg: SyncConfig,
    cache: NarInfoCache,
) -> tuple[set[StoreHash], set[NarUrl]]:
    """Traverse a local store closure for GC using NarInfoCache with disk fallback."""
    roots: set[StoreHash] = set()
    for release in releases:
        try:
            roots.update(read_store_root_hashes(release / "store-paths.xz"))
        except (OSError, lzma.LZMAError, EOFError, ValueError) as e:
            raise AbortGCError(f"Cannot read store paths for {release}: {e}") from e

    seen = set(roots)
    queue: deque[StoreHash] = deque(roots)
    resolved: set[StoreHash] = set()
    closure_nar: set[NarUrl] = set()
    disk_reads = 0
    missing_roots = 0
    executor: ThreadPoolExecutor | None = None
    last_progress = time.monotonic()

    def visit(store_hash: StoreHash, meta: NarInfo) -> None:
        resolved.add(store_hash)
        closure_nar.add(meta.url)
        for ref in meta.refs:
            if ref not in seen:
                seen.add(ref)
                queue.append(ref)

    try:
        while queue:
            to_read: list[StoreHash] = []
            while queue:
                store_hash = queue.popleft()
                if store_hash not in present:
                    _ignore_or_abort_missing(store_hash, roots)
                    missing_roots += 1
                elif (meta := cache.get(store_hash)) is not None:
                    visit(store_hash, meta)
                else:
                    to_read.append(store_hash)
                    if len(to_read) >= GC_READ_BATCH_SIZE:
                        break
            if to_read:
                if executor is None:
                    executor = ThreadPoolExecutor(max_workers=cfg.query_threads)
                for store_hash, meta, err in read_narinfo_batch(
                    to_read, cfg.working_dir, executor
                ):
                    if err is not None or meta is None:
                        _ignore_or_abort_missing(store_hash, roots, err)
                        missing_roots += 1
                        continue
                    cache.set(store_hash, meta)
                    disk_reads += 1
                    visit(store_hash, meta)
                if (now := time.monotonic()) - last_progress >= GC_PROGRESS_INTERVAL:
                    logger.info(
                        "Closure scan progress: resolved=%d disk_reads=%d pending=%d",
                        len(resolved),
                        disk_reads,
                        len(queue),
                    )
                    last_progress = now
    finally:
        if executor is not None:
            executor.shutdown(wait=True)

    if disk_reads > 0:
        logger.info("Loaded %d unindexed narinfo files from disk", disk_reads)
    if missing_roots > 0:
        logger.info("Skipped %d missing root narinfos", missing_roots)
    if not resolved:
        raise AbortGCError("No retained root narinfos resolved")
    return resolved, closure_nar


def scan_channel_symlinks(
    cfg: SyncConfig, releases_dir: Path
) -> tuple[set[Path], list[Path]]:
    published: set[Path] = set()
    update_symlinks: list[Path] = []
    with os.scandir(cfg.working_dir) as it:
        for entry in it:
            if not entry.is_symlink():
                continue
            path = Path(entry.path)
            if entry.name.startswith("."):
                if entry.name.endswith(".update"):
                    update_symlinks.append(path)
                continue
            try:
                target = path.resolve(strict=True)
            except OSError:
                logger.warning("Ignoring broken channel symlink %s", entry.name)
                continue
            if target.parent == releases_dir:
                published.add(target)
    return published, update_symlinks


def select_retained_releases(
    cfg: SyncConfig,
    releases_dir: Path,
    published: set[Path],
) -> tuple[set[Path], set[Path]]:
    now = datetime.now(UTC)
    threshold = now - timedelta(days=cfg.retain_days)
    clone_since = now - timedelta(days=cfg.clone_since_days)
    alive: set[Path] = set(published)
    latest: dict[str, tuple[datetime, Path]] = {}
    release_dirs: set[Path] = set()

    with os.scandir(releases_dir) as it:
        for entry in it:
            if not entry.is_dir(follow_symlinks=False):
                continue
            rel = Path(entry.path).resolve()
            release_dirs.add(rel)
            if not (rel / "binary-cache-url").exists():
                continue
            try:
                date_str = (rel / ".released-time").read_text(encoding="utf-8").strip()
                released = datetime.fromisoformat(date_str).replace(tzinfo=UTC)
            except (OSError, ValueError) as e:
                raise AbortGCError(
                    f"Cannot read valid .released-time for {rel}: {e}"
                ) from e
            if released < clone_since:
                continue
            if released >= threshold:
                alive.add(rel)
            channel = rel.name.split("@")[0]
            if channel not in latest or latest[channel][0] < released:
                latest[channel] = (released, rel)

    alive.update(rel for _, rel in latest.values())
    return alive, release_dirs - alive


def sweep_nar_dir(nar_dir: Path, closure_nar: set[NarUrl]) -> int:
    """Delete unreferenced NAR files (and any stray temp files) in store/nar."""
    if not nar_dir.is_dir():
        return 0
    with os.scandir(nar_dir) as it:
        return sum(
            _try_unlink(Path(entry.path))
            for entry in it
            if entry.is_file(follow_symlinks=False)
            and f"nar/{entry.name}" not in closure_nar
        )


def sweep_store_dir(
    store_dir: Path,
    unreferenced: set[StoreHash],
    cache: NarInfoCache,
) -> int:
    """Delete unreferenced .narinfo files and evict missing entries from cache."""
    deleted = 0
    for store_hash in unreferenced:
        path = store_dir / f"{store_hash}.narinfo"
        if _try_unlink(path):
            deleted += 1
            cache.remove(store_hash)
        elif not path.exists():
            cache.remove(store_hash)
    return deleted


def garbage_collect(
    cfg: SyncConfig,
    cache: NarInfoCache,
    present: set[StoreHash] | None = None,
) -> bool:
    logger.info("Collecting garbage")
    releases_dir = (cfg.working_dir / RELEASES_DIR).resolve()
    store_dir = cfg.working_dir / STORE_DIR
    published, update_symlinks = scan_channel_symlinks(cfg, releases_dir)
    try:
        alive, stale_releases = select_retained_releases(cfg, releases_dir, published)
        logger.info("Releases: alive=%d stale=%d", len(alive), len(stale_releases))
        if present is None:
            present = scan_store_dir(store_dir)
        cache.prune_missing(present)
        closure, closure_nar = collect_local_closure(alive, present, cfg, cache)
    except AbortGCError as e:
        logger.warning("Skipping GC: %s", e)
        return False

    logger.info("Closure: narinfo=%d nar=%d", len(closure), len(closure_nar))
    deleted_ni = sweep_store_dir(store_dir, present - closure, cache)
    deleted_nar = sweep_nar_dir(store_dir / "nar", closure_nar)
    for symlink in update_symlinks:
        symlink.unlink(missing_ok=True)

    deleted_releases = 0
    for rel in stale_releases:
        try:
            shutil.rmtree(rel)
            deleted_releases += 1
        except OSError as e:
            logger.warning("Failed to delete stale release %s: %r", rel, e)

    logger.info(
        "Sweep complete: narinfo=%d nar=%d releases=%d",
        deleted_ni,
        deleted_nar,
        deleted_releases,
    )
    return True
