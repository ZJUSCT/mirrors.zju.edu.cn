import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

import httpx2

from .config import (
    STORE_DIR,
    NarUrl,
    StoreHash,
    SyncConfig,
    VerificationError,
    atomic_write_text,
)
from .http import WORKER_ERRORS, download, get_text
from .narinfo import (
    NarInfo,
    NarInfoCache,
    read_narinfo_file,
    read_store_root_hashes,
    verify_nar_file,
)

logger = logging.getLogger(__name__)


def accept_local_nar(dest: Path, meta: NarInfo) -> bool:
    if not dest.is_file():
        return False
    if dest.stat().st_size == meta.file_size:
        return True
    try:
        verify_nar_file(dest, meta)
        return True
    except (OSError, VerificationError) as e:
        logger.warning(
            "Local NAR verification failed for %s; re-downloading: %r", dest, e
        )
        return False


def read_channel_upstream(channel_dir: Path) -> str:
    return (
        (channel_dir / ".original-binary-cache-url")
        .read_text(encoding="utf-8")
        .strip()
        .rstrip("/")
    )


async def queue_worker[T](
    queue: asyncio.Queue[T], process: Callable[[T], Awaitable[None]]
) -> None:
    with suppress(asyncio.QueueShutDown):
        while True:
            await process(await queue.get())
            # Failed jobs abort the TaskGroup instead of waiting for join().
            queue.task_done()


@dataclass
class StoreSyncer:
    cfg: SyncConfig
    cache: NarInfoCache
    present: set[StoreHash]
    client: httpx2.AsyncClient
    query_client: httpx2.AsyncClient
    accepted_nars: set[NarUrl] = field(default_factory=set)
    synced_paths: set[StoreHash] = field(default_factory=set)

    async def fetch_narinfo(
        self, hash_key: StoreHash, upstream: str
    ) -> tuple[NarInfo, bool]:
        if (cached := self.cache.get(hash_key)) is not None:
            return cached, False
        path = self.cfg.working_dir / STORE_DIR / f"{hash_key}.narinfo"
        if hash_key in self.present:
            try:
                meta = await asyncio.to_thread(
                    read_narinfo_file, hash_key, self.cfg.working_dir
                )
            except FileNotFoundError:
                self.present.discard(hash_key)
            except (KeyError, OSError, ValueError) as e:
                logger.warning(
                    "Corrupted local narinfo %s; re-downloading: %r", hash_key, e
                )
                await asyncio.to_thread(path.unlink, missing_ok=True)
                self.present.discard(hash_key)
            else:
                self.cache.set(hash_key, meta)
                return meta, False

        url = f"{upstream}/{hash_key}.narinfo"
        text = await get_text(self.query_client, url)
        try:
            meta = NarInfo.parse(text)
        except (KeyError, ValueError) as e:
            raise VerificationError(f"Invalid narinfo from {url}: {e}") from e
        await asyncio.to_thread(atomic_write_text, path, text)
        self.present.add(hash_key)
        self.cache.set(hash_key, meta)
        return meta, True

    async def sync_closure(
        self, roots: list[StoreHash], upstream: str, channel: str | None = None
    ) -> set[StoreHash]:
        """Resolve a closure and download its NARs with fixed numbers of workers."""
        root_set = set(roots) - self.synced_paths
        if not root_set:
            return set()

        prefix = f"{channel}: " if channel else ""
        # Workers also produce dependencies, so bounding this queue could deadlock.
        pending: asyncio.Queue[StoreHash] = asyncio.Queue()
        for store_hash in root_set:
            pending.put_nowait(store_hash)
        nars: asyncio.Queue[NarInfo] = asyncio.Queue(maxsize=self.cfg.download_queue)
        seen = self.synced_paths | root_set
        resolved: set[StoreHash] = set()
        seen_nars: set[NarUrl] = set()
        downloaded = 0
        narinfo_downloaded = 0
        missing_roots = 0

        async def resolve(store_hash: StoreHash) -> None:
            nonlocal narinfo_downloaded, missing_roots
            try:
                meta, fetched = await self.fetch_narinfo(store_hash, upstream)
            except httpx2.HTTPStatusError as e:
                if store_hash not in root_set or e.response.status_code not in (
                    403,
                    404,
                ):
                    raise
                missing_roots += 1
                logger.debug(
                    "%sskipping missing root %s.narinfo: %r", prefix, store_hash, e
                )
                return

            if fetched:
                narinfo_downloaded += 1
                logger.debug(
                    "%s[%d narinfo] %s.narinfo", prefix, narinfo_downloaded, store_hash
                )

            resolved.add(store_hash)
            for ref in meta.refs:
                if ref not in seen:
                    seen.add(ref)
                    pending.put_nowait(ref)
            if meta.url not in seen_nars:
                seen_nars.add(meta.url)
                if meta.url not in self.accepted_nars:
                    dest = self.cfg.working_dir / STORE_DIR / meta.url
                    if await asyncio.to_thread(accept_local_nar, dest, meta):
                        self.accepted_nars.add(meta.url)
                    else:
                        await nars.put(meta)

        async def sync_nar(meta: NarInfo) -> None:
            nonlocal downloaded
            dest = self.cfg.working_dir / STORE_DIR / meta.url
            await download(self.client, f"{upstream}/{meta.url}", dest, nar_meta=meta)
            downloaded += 1
            logger.debug("%s[%d nar] %s", prefix, downloaded, meta.url)
            self.accepted_nars.add(meta.url)

        async def log_progress() -> None:
            while True:
                await asyncio.sleep(15)
                logger.info(
                    "%sprogress: pending=%d nars=%d/%d resolved=%d narinfo=%d nar=%d",
                    prefix,
                    pending.qsize(),
                    nars.qsize(),
                    self.cfg.download_queue,
                    len(resolved),
                    narinfo_downloaded,
                    downloaded,
                )

        async with asyncio.TaskGroup() as group:
            progress_task = group.create_task(log_progress())
            for _ in range(self.cfg.query_threads):
                group.create_task(queue_worker(pending, resolve))
            for _ in range(self.cfg.threads):
                group.create_task(queue_worker(nars, sync_nar))
            await pending.join()
            pending.shutdown()
            await nars.join()
            nars.shutdown()
            progress_task.cancel()

        logger.info(
            "%sclosure complete: resolved=%d unique_nars=%d "
            "downloaded_narinfo=%d downloaded_nar=%d missing_roots=%d",
            prefix,
            len(resolved),
            len(seen_nars),
            narinfo_downloaded,
            downloaded,
            missing_roots,
        )
        if not resolved and root_set.issuperset(roots):
            raise VerificationError("All root .narinfo lookups were missing")
        return resolved

    async def sync_channel(self, channel: str) -> bool:
        chan_path = self.cfg.working_dir / channel
        chan_update = self.cfg.working_dir / f".{channel}.update"
        upstream = read_channel_upstream(chan_update)

        roots = read_store_root_hashes(chan_update / "store-paths.xz")
        logger.info("%s: syncing store (%d root paths)", channel, len(roots))
        try:
            resolved = await self.sync_closure(roots, upstream, channel=channel)
        except* WORKER_ERRORS as errors:
            for error in errors.exceptions:
                logger.error("%s: store sync failed: %r", channel, error)
        else:
            self.synced_paths.update(resolved)
            atomic_write_text(
                chan_update / "binary-cache-url", self.cfg.binary_cache_url
            )
            chan_update.replace(chan_path)
            logger.info("%s: store synced, symlink updated", channel)
            return True
        return False


async def sync_stores(
    channels: list[str],
    cfg: SyncConfig,
    cache: NarInfoCache,
    present: set[StoreHash],
    client: httpx2.AsyncClient,
    query_client: httpx2.AsyncClient,
) -> bool:
    logger.info("Updating binary cache (%d staged channels)", len(channels))
    upstream = read_channel_upstream(cfg.working_dir / f".{channels[0]}.update")
    dest = cfg.working_dir / STORE_DIR / "nix-cache-info"
    logger.info("Downloading nix-cache-info")
    try:
        await download(client, f"{upstream}/nix-cache-info", dest)
    except WORKER_ERRORS as e:
        logger.warning("Failed to download nix-cache-info from %s: %r", upstream, e)
        if not (dest.is_file() and dest.stat().st_size > 0):
            logger.error("No nix-cache-info available; aborting binary cache update")
            return False
        logger.warning("Using existing nix-cache-info after download failure")

    syncer = StoreSyncer(cfg, cache, present, client, query_client)
    results = [await syncer.sync_channel(c) for c in channels]
    return all(results)
