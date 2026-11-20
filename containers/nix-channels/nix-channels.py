#!/usr/bin/env python3
"""Sync NixOS/nixpkgs channels and cache.nixos.org binary cache closures.

Adapted from tuna/tunasync-scripts (nix-channels.py):
https://github.com/tuna/tunasync-scripts/blob/master/nix-channels.py
"""

import asyncio
import bz2
import gzip
import hashlib
import logging
import lzma
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zlib
from collections import Counter
from collections.abc import Awaitable, Callable
from compression import zstd
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, NamedTuple, NewType, Self

import httpx2
from bs4 import BeautifulSoup
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

STORE_DIR = "store"
RELEASES_DIR = "releases"
S3_CHANNELS_BUCKET_URL = "https://nix-channels.s3.amazonaws.com"
MAX_RETRIES = 5
CHANNEL_NAME_RE = re.compile(r"(nixos|nixpkgs)-[^/]+")
TAGLINE_RE = re.compile(r"^Released on (.+?) (?:UTC )?from")
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

NIX32_ALPHABET = "0123456789abcdfghijklmnpqrsvwxyz"

StoreHash = NewType("StoreHash", str)
NarUrl = NewType("NarUrl", str)

NAR_OPENERS = {
    "none": Path.open,
    "zstd": zstd.open,
    "xz": lzma.open,
    "bzip2": bz2.open,
    "gzip": gzip.open,
}
DECOMPRESS_ERRORS = (zstd.ZstdError, lzma.LZMAError, zlib.error, EOFError, OSError)


class VerificationError(RuntimeError):
    """Raised when a downloaded or cached file fails size or hash verification."""


class AbortGCError(RuntimeError):
    """Raised when GC integrity checks fail and collection must abort."""


WORKER_ERRORS = (OSError, ValueError, httpx2.HTTPError, VerificationError)

logger = logging.getLogger("nix-channels")

narinfo_cache: dict[StoreHash, NarInfo] = {}
# Includes existing files accepted by the FileSize check.
accepted_nars: set[NarUrl] = set()
# Updated only after a channel's closure and NAR sync have succeeded.
synced_paths: set[StoreHash] = set()


class SyncConfig(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="NIX_MIRROR_", frozen=True
    )

    working_dir: Path = Path("/data")
    base_url: str = Field(default="", min_length=1, validate_default=True)
    # Keep the existing environment variable names for worker counts.
    query_threads: int = Field(default=4, ge=1)
    threads: int = Field(default=16, ge=1)
    download_queue: int = Field(
        default_factory=lambda data: max(64, data["threads"] * 8), ge=1
    )
    delete_old: bool = True
    retain_days: float = 30.0
    clone_since_days: float = 360.0

    @property
    def binary_cache_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/{STORE_DIR}"


def hash_part(path: str) -> str:
    return sys.intern(path.split("/")[-1].split("-", 1)[0])


def file_sha256(dest: Path) -> str:
    with dest.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def to_nix32(digest: bytes) -> str:
    n = int.from_bytes(digest, "little")
    length = (len(digest) * 8 + 4) // 5
    return "".join(
        NIX32_ALPHABET[(n >> (5 * i)) & 0x1F] for i in range(length - 1, -1, -1)
    )


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    tmp = path.parent / f".{path.name}.tmp"
    try:
        tmp.write_text(content, encoding=encoding)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def atomic_symlink(link: Path, target: str) -> None:
    tmp = link.parent / f".{link.name}.tmp"
    tmp.unlink(missing_ok=True)
    try:
        tmp.symlink_to(target)
        tmp.replace(link)
    finally:
        tmp.unlink(missing_ok=True)


class NarInfo(NamedTuple):
    url: NarUrl
    compression: str
    file_size: int
    file_hash: str
    nar_size: int
    nar_hash: str
    refs: tuple[StoreHash, ...]

    @classmethod
    def parse(cls, text: str) -> Self:
        fields = {
            k: v for k, v in (line.split(": ", 1) for line in text.splitlines() if line)
        }

        if not (raw_url := fields.get("URL")):
            raise ValueError("Missing URL in narinfo")

        compression = fields.get("Compression") or "bzip2"
        if compression not in NAR_OPENERS:
            raise ValueError(f"Unsupported Compression {compression!r} in narinfo")

        return cls(
            url=NarUrl(raw_url),
            compression=compression,
            file_size=int(fields["FileSize"]),
            file_hash=fields["FileHash"],
            nar_size=int(fields["NarSize"]),
            nar_hash=fields["NarHash"],
            refs=tuple(
                StoreHash(hash_part(ref))
                for ref in fields.get("References", "").split()
            ),
        )


class ChannelStatus(StrEnum):
    UNCHANGED = "unchanged"
    STAGED = "staged"
    SKIPPED = "skipped"
    FAILED = "failed"


class ChannelResult(NamedTuple):
    status: ChannelStatus
    reason: str | None = None


def verify_nar_file(path: Path, meta: NarInfo, label: str | None = None) -> None:
    """Verify a compressed or plain NAR file against expected NarSize and NarHash."""
    desc = label or str(path)
    hasher = hashlib.sha256()
    actual_size = 0

    try:
        with NAR_OPENERS[meta.compression](path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                actual_size += len(chunk)
                if actual_size > meta.nar_size:
                    raise VerificationError(
                        f"Wrong NAR size for {desc}: expected {meta.nar_size}, "
                        f"actual >={actual_size}"
                    )
                hasher.update(chunk)
    except DECOMPRESS_ERRORS as e:
        raise VerificationError(
            f"Corrupt {meta.compression} stream for {desc}: {e}"
        ) from e

    if actual_size != meta.nar_size:
        raise VerificationError(
            f"Wrong NAR size for {desc}: expected {meta.nar_size}, actual {actual_size}"
        )
    if f"sha256:{to_nix32(hasher.digest())}" != meta.nar_hash:
        raise VerificationError(f"Wrong NAR hash for {desc}: expected {meta.nar_hash}")


def read_store_root_hashes(xz_path: Path) -> list[StoreHash]:
    with lzma.open(str(xz_path), "rt", encoding="utf-8") as f:
        return list(
            dict.fromkeys(
                StoreHash(hash_part(path)) for line in f if (path := line.rstrip())
            )
        )


def parse_channel_page(html: str) -> tuple[str, list[tuple[str, str]]] | None:
    """Parse release timestamp and file (name, sha256) rows from a channel index."""
    soup = BeautifulSoup(html, "html.parser")
    tagline = " ".join(
        text for p in soup.find_all("p") if (text := " ".join(p.get_text().split()))
    )
    tagline_match = TAGLINE_RE.match(tagline)
    if tagline_match is None:
        logger.warning(f"    - Invalid tagline: {tagline}")
        return None
    released_time = tagline_match[1]

    files = [
        (cells[0].get_text(strip=True), cells[2].get_text(strip=True))
        for tr in soup.find_all("tr")
        if len(cells := tr.find_all("td")) == 3
    ]
    return released_time, files


def is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, (httpx2.RequestError, VerificationError)) or (
        isinstance(exc, httpx2.HTTPStatusError)
        and exc.response.status_code in RETRYABLE_STATUS_CODES
    )


def log_retry(state: RetryCallState) -> None:
    exc = state.outcome.exception() if state.outcome else None
    logger.warning(
        f"{exc!r}; retrying ({state.attempt_number}/{MAX_RETRIES}) "
        f"in {state.upcoming_sleep:.0f}s"
    )


with_retry = retry(
    retry=retry_if_exception(is_retryable),
    stop=stop_after_attempt(MAX_RETRIES + 1),
    wait=wait_exponential(multiplier=1, min=1, max=16),
    before_sleep=log_retry,
    reraise=True,
)


@with_retry
async def get_text(
    client: httpx2.AsyncClient,
    url: str,
    params: dict[str, str] | None = None,
) -> str:
    res = await client.get(url, params=params)
    res.raise_for_status()
    return res.text


@with_retry
async def get_header(client: httpx2.AsyncClient, url: str, header: str) -> str:
    async with client.stream("GET", url, follow_redirects=False) as res:
        if res.is_error:
            res.raise_for_status()
        if (val := res.headers.get(header)) is None:
            raise VerificationError(f"Missing {header!r} header from {url}")
        return val


@with_retry
async def download(
    client: httpx2.AsyncClient,
    url: str,
    dest: Path,
    expected_sha256: str | None = None,
    nar_meta: NarInfo | None = None,
) -> None:
    tmp = dest.parent / f".{dest.name}.tmp"
    try:
        async with client.stream(
            "GET", url, headers={"Accept-Encoding": "identity"}
        ) as res:
            res.raise_for_status()
            hasher = hashlib.sha256()
            with tmp.open("wb") as f:
                async for chunk in res.aiter_raw(chunk_size=1024 * 1024):
                    f.write(chunk)
                    hasher.update(chunk)
            if expected_sha256 is not None and hasher.hexdigest() != expected_sha256:
                raise VerificationError(
                    f"Wrong hash for {url}: expected {expected_sha256}"
                )
            if nar_meta is not None and (
                f"sha256:{to_nix32(hasher.digest())}" != nar_meta.file_hash
                or tmp.stat().st_size != nar_meta.file_size
            ):
                # Recompression can change FileHash/FileSize without changing the NAR.
                await asyncio.to_thread(verify_nar_file, tmp, nar_meta, label=url)
        tmp.rename(dest)
    finally:
        tmp.unlink(missing_ok=True)


async def list_s3_channels(client: httpx2.AsyncClient) -> list[tuple[str, datetime]]:
    channels: list[tuple[str, datetime]] = []
    token: str | None = None
    while True:
        params = {"list-type": "2", "delimiter": "/"}
        if token is not None:
            params["continuation-token"] = token
        xml_text = await get_text(client, S3_CHANNELS_BUCKET_URL, params=params)
        root = ET.fromstring(xml_text)
        for contents in root.findall("{*}Contents"):
            name = contents.findtext("{*}Key")
            if name is None or not CHANNEL_NAME_RE.fullmatch(name):
                continue
            modified = datetime.fromisoformat(
                contents.findtext("{*}LastModified") or ""
            )
            channels.append((name, modified))
        if root.findtext("{*}IsTruncated") != "true":
            return channels
        token = root.findtext("{*}NextContinuationToken")


async def sync_release_files(
    chan_location: str,
    release_path: Path,
    files: list[tuple[str, str]],
    client: httpx2.AsyncClient,
) -> bool:
    logger.info("    - Downloading files")
    ok = True
    for file_name, file_hash in files:
        if file_name.endswith((".ova", ".iso")):
            continue
        is_bcu = file_name == "binary-cache-url"
        dest_path = release_path / (
            ".original-binary-cache-url" if is_bcu else file_name
        )
        if dest_path.exists() and file_sha256(dest_path) == file_hash:
            logger.info(f"      - {file_name} (existing)")
            continue
        logger.info(
            f"      - {'binary-cache-url (redirected)' if is_bcu else file_name}"
        )
        try:
            await download(
                client,
                f"{chan_location}/{file_name}",
                dest_path,
                expected_sha256=file_hash,
            )
        except WORKER_ERRORS as e:
            ok = False
            logger.error(f"        Download failed: {e!r}")

    return ok


async def sync_channel(
    channel: str, cfg: SyncConfig, client: httpx2.AsyncClient
) -> ChannelResult:
    chan_location = await get_header(
        client,
        f"{S3_CHANNELS_BUCKET_URL}/{channel}",
        "x-amz-website-redirect-location",
    )
    chan_release = chan_location.split("/")[-1]
    release_target = f"{RELEASES_DIR}/{channel}@{chan_release}"

    chan_path = cfg.working_dir / channel
    if chan_path.is_symlink() and os.readlink(chan_path) == release_target:
        return ChannelResult(ChannelStatus.UNCHANGED)

    chan_update = cfg.working_dir / f".{channel}.update"
    if chan_update.is_symlink() and os.readlink(chan_update) == release_target:
        logger.info(f"  - {channel} ready to update to {chan_release}")
        return ChannelResult(ChannelStatus.STAGED)

    logger.info(f"  - {channel} -> {chan_release}")
    try:
        html = await get_text(client, chan_location)
    except httpx2.HTTPStatusError as e:
        if e.response.status_code != 404:
            raise
        return ChannelResult(ChannelStatus.SKIPPED, "Release index not found")
    if (release_meta := parse_channel_page(html)) is None:
        return ChannelResult(ChannelStatus.SKIPPED, "Invalid release index")
    released_time, files = release_meta

    release_path = cfg.working_dir / release_target
    release_path.mkdir(parents=True, exist_ok=True)
    atomic_write_text(release_path / ".released-time", released_time)

    if not await sync_release_files(chan_location, release_path, files, client):
        logger.warning("    - Found bad files. Not updating symlink.")
        return ChannelResult(ChannelStatus.FAILED, "Release file download failed")

    atomic_symlink(chan_update, release_target)
    logger.info("    - Symlink updated")
    return ChannelResult(ChannelStatus.STAGED)


async def sync_channels(
    cfg: SyncConfig, client: httpx2.AsyncClient
) -> dict[str, ChannelResult]:
    logger.info("- Fetching channels")
    clone_since = datetime.now(UTC) - timedelta(days=cfg.clone_since_days)
    results: dict[str, ChannelResult] = {}
    for channel, modified in await list_s3_channels(client):
        if modified < clone_since:
            continue
        try:
            result = await sync_channel(channel, cfg, client)
        except WORKER_ERRORS as e:
            result = ChannelResult(ChannelStatus.FAILED, str(e))
        results[channel] = result
        if result.status is ChannelStatus.FAILED:
            logger.error(f"  - Failed to sync {channel}: {result.reason}")
        elif result.status is ChannelStatus.SKIPPED:
            logger.warning(f"  - Skipping {channel}: {result.reason}")

    counts = Counter(result.status for result in results.values())
    logger.info(
        "  - Channel preparation: "
        + ", ".join(f"{counts[status]} {status.value}" for status in ChannelStatus)
    )
    return results


def read_local_narinfo(hash_key: StoreHash, working_dir: Path) -> NarInfo:
    if (cached := narinfo_cache.get(hash_key)) is not None:
        return cached
    path = working_dir / STORE_DIR / f"{hash_key}.narinfo"
    meta = NarInfo.parse(path.read_text(encoding="utf-8"))
    narinfo_cache[hash_key] = meta
    return meta


async def fetch_narinfo(
    hash_key: StoreHash, working_dir: Path, upstream: str, client: httpx2.AsyncClient
) -> tuple[NarInfo, bool]:
    if (cached := narinfo_cache.get(hash_key)) is not None:
        return cached, False
    path = working_dir / STORE_DIR / f"{hash_key}.narinfo"
    try:
        return await asyncio.to_thread(read_local_narinfo, hash_key, working_dir), False
    except FileNotFoundError:
        pass
    except (KeyError, OSError, ValueError) as e:
        logger.warning(f"Corrupted local narinfo {hash_key}, re-downloading: {e!r}")
        await asyncio.to_thread(path.unlink, missing_ok=True)

    url = f"{upstream}/{hash_key}.narinfo"
    text = await get_text(client, url)
    try:
        meta = NarInfo.parse(text)
    except (KeyError, ValueError) as e:
        raise VerificationError(f"Invalid narinfo from {url}: {e}") from e
    await asyncio.to_thread(atomic_write_text, path, text)
    narinfo_cache[hash_key] = meta
    return meta, True


async def queue_worker[T](
    queue: asyncio.Queue[T], process: Callable[[T], Awaitable[None]]
) -> None:
    with suppress(asyncio.QueueShutDown):
        while True:
            await process(await queue.get())
            # Failed jobs abort the TaskGroup instead of waiting for join().
            queue.task_done()


async def sync_closure(
    roots: list[StoreHash],
    cfg: SyncConfig,
    upstream: str,
    client: httpx2.AsyncClient,
    query_client: httpx2.AsyncClient,
) -> set[StoreHash]:
    """Resolve a closure and download its NARs with fixed numbers of workers."""
    root_set = set(roots) - synced_paths
    if not root_set:
        return set()

    # Workers also produce dependencies, so bounding this queue could deadlock.
    pending: asyncio.Queue[StoreHash] = asyncio.Queue()
    for store_hash in root_set:
        pending.put_nowait(store_hash)
    nars: asyncio.Queue[NarInfo] = asyncio.Queue(maxsize=cfg.download_queue)
    seen = synced_paths | root_set
    resolved: set[StoreHash] = set()
    seen_nars: set[NarUrl] = set()
    downloaded = 0
    narinfo_downloaded = 0

    async def resolve(store_hash: StoreHash) -> None:
        nonlocal narinfo_downloaded
        try:
            meta, fetched = await fetch_narinfo(
                store_hash, cfg.working_dir, upstream, query_client
            )
        except httpx2.HTTPStatusError as e:
            if store_hash not in root_set or e.response.status_code not in (403, 404):
                raise
            logger.warning(f"    - Skipping missing root {store_hash}.narinfo: {e}")
            return

        if fetched:
            narinfo_downloaded += 1
            logger.info(f"    - [{narinfo_downloaded} narinfo] {store_hash}.narinfo")

        resolved.add(store_hash)
        for ref in meta.refs:
            if ref not in seen:
                seen.add(ref)
                pending.put_nowait(ref)
        if meta.url not in seen_nars:
            seen_nars.add(meta.url)
            if meta.url not in accepted_nars:
                dest = cfg.working_dir / STORE_DIR / meta.url
                if await asyncio.to_thread(accept_local_nar, dest, meta):
                    accepted_nars.add(meta.url)
                else:
                    await nars.put(meta)

    async def sync_nar(meta: NarInfo) -> None:
        nonlocal downloaded
        dest = cfg.working_dir / STORE_DIR / meta.url
        await download(client, f"{upstream}/{meta.url}", dest, nar_meta=meta)
        downloaded += 1
        logger.info(f"    - [{downloaded} nar] {meta.url}")
        accepted_nars.add(meta.url)

    async def log_progress() -> None:
        while True:
            await asyncio.sleep(15)
            logger.info(
                f"    - [progress] pending={pending.qsize()} "
                f"nars={nars.qsize()}/{cfg.download_queue} "
                f"resolved={len(resolved)} narinfo={narinfo_downloaded} nar={downloaded}"
            )

    async with asyncio.TaskGroup() as group:
        progress_task = group.create_task(log_progress())
        for _ in range(cfg.query_threads):
            group.create_task(queue_worker(pending, resolve))
        for _ in range(cfg.threads):
            group.create_task(queue_worker(nars, sync_nar))
        await pending.join()
        pending.shutdown()
        await nars.join()
        nars.shutdown()
        progress_task.cancel()

    logger.info(
        f"    - {len(resolved)} closure paths resolved, {len(seen_nars)} unique NARs "
        f"({downloaded} downloaded)"
    )
    if not resolved and root_set.issuperset(roots):
        raise VerificationError("All root .narinfo lookups were missing")
    return resolved


async def collect_local_closure(
    releases: set[Path],
    cfg: SyncConfig,
    best_effort: bool = False,
    skip_hashes: set[StoreHash] | None = None,
) -> tuple[set[StoreHash], set[NarUrl]]:
    """Traverse a local store closure for GC without network access."""
    roots: set[StoreHash] = set()
    for release in releases:
        try:
            xz_path = release / "store-paths.xz"
            roots.update(await asyncio.to_thread(read_store_root_hashes, xz_path))
        except (OSError, lzma.LZMAError, EOFError, ValueError) as e:
            if not best_effort:
                raise AbortGCError(f"Cannot read store paths for {release}: {e}") from e
            logger.warning(f"Cannot read staged store paths for {release}: {e}")

    seen = set(skip_hashes or ())
    root_pending = [h for h in roots if h not in seen]
    if not root_pending:
        return set(), set()

    pending: asyncio.Queue[StoreHash] = asyncio.Queue()
    for store_hash in root_pending:
        pending.put_nowait(store_hash)
    seen.update(roots)
    resolved: set[StoreHash] = set()
    closure_nar: set[NarUrl] = set()

    async def resolve(store_hash: StoreHash) -> None:
        if (meta := narinfo_cache.get(store_hash)) is None:
            try:
                meta = await asyncio.to_thread(
                    read_local_narinfo, store_hash, cfg.working_dir
                )
            except (KeyError, OSError, ValueError) as e:
                if best_effort:
                    return
                if store_hash in roots and isinstance(e, FileNotFoundError):
                    logger.warning(f"Missing root narinfo {store_hash}; skipping in GC")
                    return
                raise AbortGCError(
                    f"Missing or invalid retained narinfo {store_hash}: {e}"
                ) from e

        resolved.add(store_hash)
        closure_nar.add(meta.url)
        for ref in meta.refs:
            if ref not in seen:
                seen.add(ref)
                pending.put_nowait(ref)

    try:
        async with asyncio.TaskGroup() as group:
            for _ in range(cfg.query_threads):
                group.create_task(queue_worker(pending, resolve))
            await pending.join()
            pending.shutdown()
    except* AbortGCError as errors:
        raise errors.exceptions[0] from errors

    if not resolved and not best_effort:
        raise AbortGCError("No retained root narinfos resolved")
    return resolved, closure_nar


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
            f"Local NAR verification failed for {dest}, re-downloading: {e!r}"
        )
        return False


def read_channel_upstream(channel_dir: Path) -> str:
    return (channel_dir / ".original-binary-cache-url").read_text().strip().rstrip("/")


async def sync_channel_store(
    channel: str,
    cfg: SyncConfig,
    client: httpx2.AsyncClient,
    query_client: httpx2.AsyncClient,
) -> bool:
    logger.info(f"  - {channel}")
    chan_path = cfg.working_dir / channel
    chan_update = cfg.working_dir / f".{channel}.update"
    upstream = read_channel_upstream(chan_update)

    roots = read_store_root_hashes(chan_update / "store-paths.xz")
    logger.info(f"    - {len(roots)} paths listed")
    try:
        resolved = await sync_closure(
            roots, cfg, upstream, client, query_client=query_client
        )
    except* WORKER_ERRORS as errors:
        for error in errors.exceptions:
            logger.error(f"    - Failed to sync {channel}: {error!r}")
    else:
        synced_paths.update(resolved)
        atomic_write_text(chan_update / "binary-cache-url", cfg.binary_cache_url)
        chan_update.rename(chan_path)
        logger.info("    - Finished with success, symlink updated")
        return True
    return False


async def sync_stores(
    channels: list[str],
    cfg: SyncConfig,
    client: httpx2.AsyncClient,
    query_client: httpx2.AsyncClient,
) -> bool:
    logger.info("- Updating binary cache")
    if not channels:
        return True
    upstreams = dict.fromkeys(
        read_channel_upstream(cfg.working_dir / f".{channel}.update")
        for channel in channels
    )
    dest = cfg.working_dir / STORE_DIR / "nix-cache-info"
    logger.info("  - Downloading nix-cache-info")
    for upstream in upstreams:
        try:
            await download(client, f"{upstream}/nix-cache-info", dest)
            break
        except WORKER_ERRORS as e:
            logger.warning(
                f"    - Failed to download nix-cache-info from {upstream}: {e!r}"
            )
    else:
        if not (dest.is_file() and dest.stat().st_size > 0):
            logger.error(
                "    - No nix-cache-info available; aborting binary cache update"
            )
            return False
        logger.warning("    - Using existing nix-cache-info after download failure")

    results = [
        await sync_channel_store(c, cfg, client, query_client=query_client)
        for c in channels
    ]
    return all(results)


def scan_channel_symlinks(
    cfg: SyncConfig, releases_dir: Path
) -> tuple[set[Path], set[Path], list[Path]]:
    published: set[Path] = set()
    staged: set[Path] = set()
    stale_update_symlinks: list[Path] = []
    with os.scandir(cfg.working_dir) as it:
        for entry in it:
            if not entry.is_symlink():
                continue
            path = Path(entry.path)
            is_update = entry.name.startswith(".") and entry.name.endswith(".update")
            is_tmp = entry.name.startswith(".") and entry.name.endswith(".tmp")
            if is_tmp:
                stale_update_symlinks.append(path)
                continue
            if entry.name.startswith(".") and not is_update:
                continue
            try:
                target = path.resolve(strict=True)
            except OSError:
                target = None
                if not is_update:
                    logger.warning(
                        f"Ignoring broken channel symlink {entry.name} in GC"
                    )
            if target is None or target.parent != releases_dir:
                if is_update:
                    stale_update_symlinks.append(path)
                continue
            (staged if is_update else published).add(target)
    return published, staged, stale_update_symlinks


def select_retained_releases(
    cfg: SyncConfig,
    releases_dir: Path,
    published: set[Path],
    staged: set[Path],
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
                date_str = (rel / ".released-time").read_text().strip()
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
    return alive, release_dirs - alive - staged


def sweep_dir(
    directory: Path,
    should_delete: Callable[[str], bool],
    delete_old: bool,
) -> tuple[int, int]:
    """Count (and optionally delete) unreferenced files and orphan .tmp files."""
    if not directory.is_dir():
        return 0, 0
    deleted = 0
    deleted_tmp = 0
    with os.scandir(directory) as it:
        for entry in it:
            if not entry.is_file(follow_symlinks=False):
                continue
            is_tmp = entry.name.startswith(".") and entry.name.endswith(".tmp")
            if not is_tmp and not should_delete(entry.name):
                continue
            if delete_old:
                try:
                    Path(entry.path).unlink()
                except FileNotFoundError:
                    continue
                except OSError as e:
                    logger.warning(f"Failed to delete {entry.path}: {e}")
                    continue
            if is_tmp:
                deleted_tmp += 1
            else:
                deleted += 1
    return deleted, deleted_tmp


async def garbage_collect(cfg: SyncConfig) -> bool:
    logger.info("- Collecting garbage")
    releases_dir = (cfg.working_dir / RELEASES_DIR).resolve()
    published, staged, stale_update_symlinks = scan_channel_symlinks(cfg, releases_dir)
    try:
        alive, stale_releases = select_retained_releases(
            cfg, releases_dir, published, staged
        )
        logger.info(
            f"  - {len(alive)} releases alive, {len(staged - alive)} staged "
            f"({len(stale_releases)} stale)"
        )
        closure, closure_nar = await collect_local_closure(alive, cfg)
    except AbortGCError as e:
        logger.warning(f"Skipping GC: {e}")
        return False

    staged_closure, staged_nars = await collect_local_closure(
        staged - alive, cfg, best_effort=True, skip_hashes=closure
    )
    closure.update(staged_closure)
    closure_nar.update(staged_nars)

    logger.info(f"  - {len(closure)} narinfo files in closure")
    logger.info(f"  - {len(closure_nar)} nar files in closure")

    deleted_ni, store_tmp = sweep_dir(
        cfg.working_dir / STORE_DIR,
        lambda name: (
            name.endswith(".narinfo") and name.removesuffix(".narinfo") not in closure
        ),
        cfg.delete_old,
    )
    deleted_nar, nar_tmp = sweep_dir(
        cfg.working_dir / STORE_DIR / "nar",
        lambda name: f"nar/{name}" not in closure_nar,
        cfg.delete_old,
    )
    deleted_tmp = store_tmp + nar_tmp
    for rel in alive | staged:
        _, rel_tmp = sweep_dir(rel, lambda _: False, cfg.delete_old)
        deleted_tmp += rel_tmp

    deleted_releases = 0 if cfg.delete_old else len(stale_releases)
    if cfg.delete_old:
        for symlink in stale_update_symlinks:
            symlink.unlink(missing_ok=True)
        for rel in stale_releases:
            try:
                shutil.rmtree(rel)
                deleted_releases += 1
            except OSError as e:
                logger.warning(f"Failed to delete stale release {rel}: {e}")

    status = "deleted" if cfg.delete_old else "unreachable"
    logger.info(f"  - {deleted_ni} narinfo files {status}")
    logger.info(f"  - {deleted_nar} nar files {status}")
    logger.info(f"  - {deleted_tmp} orphan tmp files {status}")
    logger.info(f"  - {deleted_releases} stale release directories {status}")
    return True


async def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s] %(levelname)-8s %(message)s"
    )
    logging.getLogger("httpx2").setLevel(logging.WARNING)
    cfg = SyncConfig()
    asyncio.get_running_loop().set_default_executor(
        ThreadPoolExecutor(max_workers=max(32, cfg.query_threads + cfg.threads))
    )
    (cfg.working_dir / RELEASES_DIR).mkdir(parents=True, exist_ok=True)
    (cfg.working_dir / STORE_DIR / "nar").mkdir(parents=True, exist_ok=True)
    limits = httpx2.Limits(max_connections=None, max_keepalive_connections=cfg.threads)
    query_limits = httpx2.Limits(max_connections=None, max_keepalive_connections=4)
    async with (
        httpx2.AsyncClient(follow_redirects=True, limits=limits) as client,
        httpx2.AsyncClient(
            http2=True, follow_redirects=True, limits=query_limits
        ) as query_client,
    ):
        channel_results = await sync_channels(cfg, client)
        channels = [
            channel
            for channel, result in channel_results.items()
            if result.status is ChannelStatus.STAGED
        ]
        channels_ok = all(
            result.status is not ChannelStatus.FAILED
            for result in channel_results.values()
        )
        stores_ok = await sync_stores(channels, cfg, client, query_client=query_client)
    gc_ok = await garbage_collect(cfg)
    return 0 if channels_ok and stores_ok and gc_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
