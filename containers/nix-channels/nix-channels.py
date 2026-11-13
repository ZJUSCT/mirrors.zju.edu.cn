#!/usr/bin/env python3
"""Sync NixOS/nixpkgs channels and cache.nixos.org binary cache closures.

Adapted from tuna/tunasync-scripts (nix-channels.py):
https://github.com/tuna/tunasync-scripts/blob/master/nix-channels.py
"""

import base64
import binascii
import hashlib
import logging
import lzma
import os
import re
import sys
import threading
from collections import deque
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NamedTuple, cast

import minio
import requests
import urllib3
from pyquery import PyQuery as pq
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

WORKING_DIR = os.getenv("NIX_MIRROR_WORKING_DIR", "/data")
MIRROR_BASE_URL = os.environ["NIX_MIRROR_BASE_URL"].rstrip("/")
QUERY_THREADS = int(os.getenv("NIX_MIRROR_QUERY_THREADS", "4"))
THREADS = int(os.getenv("NIX_MIRROR_THREADS", "8"))
DOWNLOAD_QUEUE = int(os.getenv("NIX_MIRROR_DOWNLOAD_QUEUE", str(max(64, THREADS * 8))))
DELETE_OLD = os.getenv("NIX_MIRROR_DELETE_OLD", "1") == "1"
RETAIN_DAYS = float(os.getenv("NIX_MIRROR_RETAIN_DAYS", "30"))
CLONE_SINCE_DAYS = float(os.getenv("NIX_MIRROR_CLONE_SINCE_DAYS", "360"))

if QUERY_THREADS < 1 or THREADS < 1 or DOWNLOAD_QUEUE < 1:
    raise ValueError("QUERY_THREADS, THREADS, and DOWNLOAD_QUEUE must be >= 1")

STORE_DIR = "store"
RELEASES_DIR = "releases"
NIX32_ALPHABET = "0123456789abcdfghijklmnpqrsvwxyz"
STORE_HASH_RE = re.compile(r"^[0-9a-df-np-sv-z]{32}$")
HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
HASH_DIGEST_BYTES = {"md5": 16, "sha1": 20, "sha256": 32, "sha512": 64}
CLONE_SINCE = datetime.now(UTC) - timedelta(days=CLONE_SINCE_DAYS)
TIMEOUT = 60

working_dir = Path(WORKING_DIR)
binary_cache_url = f"{MIRROR_BASE_URL}/{STORE_DIR}"

session = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
adapter = HTTPAdapter(
    pool_connections=16,
    pool_maxsize=max(16, QUERY_THREADS + THREADS + 8),
    max_retries=retries,
)
session.mount("http://", adapter)
session.mount("https://", adapter)

proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
http_client = urllib3.ProxyManager(proxy, timeout=TIMEOUT) if proxy else None
client = minio.Minio("s3.amazonaws.com", http_client=http_client)

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)-8s %(message)s"
)
logger = logging.getLogger("nix-channels")


class WrongSize(RuntimeError):
    pass


class WrongHash(RuntimeError):
    pass


class NarInfoMeta(NamedTuple):
    url: str
    file_size: int | None
    file_hash: str | None
    refs: tuple[str, ...]


RETRYABLE_ERRORS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
    urllib3.exceptions.HTTPError,
    WrongSize,
    WrongHash,
)
WORKER_ERRORS = (
    OSError,
    ValueError,
    requests.exceptions.RequestException,
    *RETRYABLE_ERRORS,
)

narinfo_lock = threading.Lock()
narinfo_cache: dict[str, NarInfoMeta] = {}
nar_lock = threading.Lock()
verified_nars: set[str] = set()


def file_sha256(dest: Path) -> str:
    with dest.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def to_nix32(digest: bytes) -> str:
    n = int.from_bytes(digest, "little")
    length = (len(digest) * 8 + 4) // 5
    return "".join(
        NIX32_ALPHABET[(n >> (5 * i)) & 0x1F] for i in range(length - 1, -1, -1)
    )


def parse_nix_hash(spec: str) -> tuple[str, str]:
    spec = spec.strip()
    if ":" in spec:
        algo, _, enc = spec.partition(":")
        if (nbytes := HASH_DIGEST_BYTES.get(algo)) is not None:
            nix32_len = (nbytes * 8 + 4) // 5
            is_nix32 = len(enc) == nix32_len and all(c in NIX32_ALPHABET for c in enc)
            is_hex = len(enc) == nbytes * 2 and bool(HEX_RE.fullmatch(enc))
            if is_nix32 or is_hex:
                return algo, spec
    elif "-" in spec:
        algo, _, enc = spec.partition("-")
        if (nbytes := HASH_DIGEST_BYTES.get(algo)) is not None:
            try:
                decoded = base64.b64decode(enc.encode("ascii"), validate=True)
            except (binascii.Error, ValueError, UnicodeEncodeError):
                decoded = b""
            if len(decoded) == nbytes:
                return algo, spec
    raise ValueError(f"Invalid Nix hash: {spec!r}")


def verify_digest(digest: bytes, expected: str) -> bool:
    algo, norm = parse_nix_hash(expected)
    if len(digest) != HASH_DIGEST_BYTES[algo]:
        return False
    if ":" in norm:
        _, _, enc = norm.partition(":")
        if len(enc) == len(digest) * 2:
            return digest.hex() == enc.lower()
        return to_nix32(digest) == enc
    return base64.b64encode(digest).decode("ascii") == norm.partition("-")[2]


def download(
    url: str,
    dest: Path,
    expected_size: int | None = None,
    expected_hash: str | None = None,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.parent / f".{dest.name}.{threading.get_ident()}.tmp"
    algo = parse_nix_hash(expected_hash)[0] if expected_hash is not None else None
    retry = retries

    while True:
        try:
            with session.get(
                url,
                headers={"Accept-Encoding": "identity"},
                timeout=TIMEOUT,
                stream=True,
            ) as res:
                res.raise_for_status()
                hdr = res.headers.get("Content-Length")
                content_encoding = res.headers.get("Content-Encoding", "").strip().lower()
                content_len = (
                    int(hdr)
                    if hdr is not None and content_encoding in ("", "identity")
                    else None
                )
                if (
                    content_len is not None
                    and expected_size is not None
                    and content_len != expected_size
                ):
                    raise WrongSize(
                        f"Wrong file size: expected {expected_size}, "
                        f"actual {content_len}"
                    )

                hasher = hashlib.new(algo) if algo else None
                actual = 0
                with tmp.open("wb") as f:
                    for chunk in res.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        if (
                            expected_size is not None
                            and actual + len(chunk) > expected_size
                        ):
                            raise WrongSize(
                                f"Wrong file size: expected {expected_size}, "
                                f"actual {actual + len(chunk)}"
                            )
                        f.write(chunk)
                        actual += len(chunk)
                        if hasher:
                            hasher.update(chunk)

                if content_len is not None and actual != content_len:
                    raise WrongSize(
                        f"Wrong file size: expected {content_len}, actual {actual}"
                    )
                if expected_size is not None and actual != expected_size:
                    raise WrongSize(
                        f"Wrong file size: expected {expected_size}, actual {actual}"
                    )
                if (
                    hasher
                    and expected_hash
                    and not verify_digest(hasher.digest(), expected_hash)
                ):
                    raise WrongHash(f"Wrong hash for {url}: expected {expected_hash}")
                break
        except RETRYABLE_ERRORS as e:
            tmp.unlink(missing_ok=True)
            logger.warning(e)
            try:
                next_retry = retry.increment(method="GET", url=url, error=e)
            except urllib3.exceptions.MaxRetryError:
                next_retry = None
            if next_retry is None:
                raise
            retry = next_retry
            logger.warning(f"Retrying download: {retry}")
            retry.sleep()
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    tmp.rename(dest)


def get_channels() -> list[tuple[str, datetime]]:
    channels: list[tuple[str, datetime]] = []
    for obj in client.list_objects("nix-channels"):
        name = obj.object_name
        if name is None or not re.fullmatch(r"(nixos|nixpkgs)-.+[^/]", name):
            continue
        if obj.last_modified is None:
            raise ValueError(f"Channel {name!r} is missing LastModified")
        channels.append((name, obj.last_modified))
    return channels


def sync_release_files(
    chan_location: str, release_path: Path, files: list[tuple[str, str]]
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
            download(
                f"{chan_location}/{file_name}",
                dest_path,
                expected_hash=f"sha256:{file_hash}",
            )
        except WORKER_ERRORS as e:
            ok = False
            logger.error(f"        Download failed: {e}")

    if not ok:
        return False

    logger.info("    - Writing binary-cache-url")
    (release_path / "binary-cache-url").write_text(binary_cache_url)
    return True


def clone_channel(channel: str) -> tuple[bool, bool]:
    chan_location = client.get_object("nix-channels", channel).headers[
        "x-amz-website-redirect-location"
    ]
    chan_release = chan_location.split("/")[-1]
    release_target = f"{RELEASES_DIR}/{channel}@{chan_release}"

    chan_path = working_dir / channel
    if chan_path.is_symlink() and os.readlink(chan_path) == release_target:
        return False, True

    chan_update = working_dir / f".{channel}.update"
    if chan_update.is_symlink() and os.readlink(chan_update) == release_target:
        logger.info(f"  - {channel} ready to update to {chan_release}")
        return True, True

    logger.info(f"  - {channel} -> {chan_release}")
    res = session.get(chan_location, timeout=TIMEOUT)
    if res.status_code == 404:
        logger.warning("    - Not found")
        return False, True
    res.raise_for_status()

    node = pq(res.text)
    tagline = cast(str, node("p").text())
    if (
        tagline_match := re.match(r"^Released on (.+?) (?:UTC )?from", tagline)
    ) is None:
        logger.warning(f"    - Invalid tagline: {tagline}")
        return False, True

    release_path = working_dir / release_target
    release_path.mkdir(parents=True, exist_ok=True)
    (release_path / ".released-time").write_text(tagline_match[1])

    files: list[tuple[str, str]] = []
    for row in node("tr"):
        td = pq(row)("td")
        if len(td) == 3:
            file_name = cast(str, pq(td[0]).text())
            file_hash = cast(str, pq(td[2]).text())
            files.append((file_name, file_hash))
    if not sync_release_files(chan_location, release_path, files):
        logger.warning("    - Found bad files. Not updating symlink.")
        return False, False

    chan_update.unlink(missing_ok=True)
    chan_update.symlink_to(release_target)
    logger.info("    - Symlink updated")
    return True, True


def clone_channels() -> tuple[list[str], bool]:
    logger.info("- Fetching channels")
    working_dir.mkdir(parents=True, exist_ok=True)
    to_update: list[str] = []
    all_ok = True
    for channel, modified in get_channels():
        if modified < CLONE_SINCE:
            continue
        needs_update, ok = clone_channel(channel)
        if needs_update:
            to_update.append(channel)
        if not ok:
            all_ok = False
    return to_update, all_ok


def hash_part(path: str) -> str:
    return path.split("/")[-1].split("-", 1)[0]


def validate_nar_url(url: str) -> str:
    parts = url.split("/")
    if (
        not url
        or url.startswith("/")
        or any(c in url for c in ":?#\\")
        or parts[0] != "nar"
        or any(p in ("", ".", "..") for p in parts)
    ):
        raise ValueError(f"Invalid NAR URL: {url!r}")
    return url


def parse_narinfo_meta(expected_hash: str, text: str) -> NarInfoMeta:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if line.strip():
            key, sep, val = line.partition(":")
            if not sep:
                raise ValueError(f"Invalid narinfo line: {line!r}")
            fields[key.strip()] = val.strip()

    url = validate_nar_url(fields.get("URL", ""))
    if (store_path := fields.get("StorePath")) and hash_part(
        store_path
    ) != expected_hash:
        raise ValueError(
            f"Narinfo StorePath hash mismatch: expected {expected_hash!r}, "
            f"got {hash_part(store_path)!r}"
        )

    file_size = int(fields["FileSize"]) if fields.get("FileSize") else None
    if file_size is not None and file_size < 0:
        raise ValueError(f"Negative FileSize {file_size} in {expected_hash}.narinfo")

    file_hash = fields.get("FileHash") or None
    if file_hash:
        parse_nix_hash(file_hash)

    refs = []
    for ref in fields.get("References", "").split():
        ref_hash = hash_part(ref)
        if not STORE_HASH_RE.fullmatch(ref_hash):
            raise ValueError(f"Invalid reference {ref!r} in {expected_hash}.narinfo")
        refs.append(ref_hash)

    return NarInfoMeta(
        url=url,
        file_size=file_size,
        file_hash=file_hash,
        refs=tuple(dict.fromkeys(refs)),
    )


def resolve_narinfo(hash_key: str, upstream: str | None = None) -> NarInfoMeta:
    with narinfo_lock:
        if (cached := narinfo_cache.get(hash_key)) is not None:
            return cached

    path = working_dir / STORE_DIR / f"{hash_key}.narinfo"
    if path.is_file():
        try:
            meta = parse_narinfo_meta(hash_key, path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            if upstream is None:
                raise
            logger.warning(f"Corrupted local narinfo {path}, re-downloading: {e}")
            path.unlink(missing_ok=True)
        else:
            with narinfo_lock:
                narinfo_cache[hash_key] = meta
            return meta

    if upstream is None:
        raise FileNotFoundError(path)

    download(f"{upstream}/{hash_key}.narinfo", path)
    try:
        meta = parse_narinfo_meta(hash_key, path.read_text(encoding="utf-8"))
    except ValueError:
        path.unlink(missing_ok=True)
        raise

    with narinfo_lock:
        narinfo_cache[hash_key] = meta
    return meta


def read_store_root_hashes(xz_path: Path) -> tuple[list[str], bool]:
    roots: dict[str, None] = {}
    had_raw = False
    with lzma.open(str(xz_path), "rt", encoding="utf-8") as f:
        for line in f:
            path = line.rstrip()
            if not path:
                continue
            had_raw = True
            # Workaround to avoid broken texlive paths in upstream channels:
            # https://github.com/tuna/issues/issues/1855
            if "texlive-2022-env-man" in path or "texlive-2022-env-info" in path:
                continue
            h = hash_part(path)
            if not STORE_HASH_RE.fullmatch(h):
                raise ValueError(f"Invalid store path {path!r} in {xz_path}")
            roots[h] = None
    return list(roots), had_raw


def walk_closure(
    roots: list[str],
    upstream: str | None = None,
    on_narinfo: Callable[[NarInfoMeta], None] | None = None,
    stop_event: threading.Event | None = None,
) -> tuple[set[str], set[str]] | None:
    """Traverse the store dependency closure concurrently via BFS from ``roots``.

    Resolves each path's ``.narinfo`` (fetching from ``upstream`` if given, or
    reading local files only when ``None``), invokes ``on_narinfo`` on the
    coordinator thread for each resolved entry, and aborts early on worker
    errors or when ``stop_event`` is set. Returns ``(store_hashes, nar_urls)``,
    or ``None`` if aborted or failed.
    """
    pending = deque(dict.fromkeys(roots))
    if not pending:
        return set(), set()

    abort = stop_event or threading.Event()
    closure = set(pending)
    closure_nar: set[str] = set()
    max_in_flight = QUERY_THREADS * 4
    in_flight: dict[Future[NarInfoMeta], str] = {}

    with ThreadPoolExecutor(max_workers=QUERY_THREADS) as pool:
        while (pending or in_flight) and not abort.is_set():
            while pending and len(in_flight) < max_in_flight and not abort.is_set():
                store_hash = pending.popleft()
                in_flight[pool.submit(resolve_narinfo, store_hash, upstream)] = (
                    store_hash
                )

            done_futs, _ = wait(in_flight, timeout=0.5, return_when=FIRST_COMPLETED)
            for fut in done_futs:
                store_hash = in_flight.pop(fut)
                try:
                    meta = fut.result()
                except WORKER_ERRORS as e:
                    abort.set()
                    for remaining in in_flight:
                        remaining.cancel()
                    if upstream is not None:
                        logger.error(
                            f"    - Failed to resolve {store_hash}.narinfo: {e}"
                        )
                    else:
                        logger.warning(
                            f"Missing or invalid retained narinfo {store_hash}; "
                            f"skipping GC: {e}"
                        )
                    return None

                closure_nar.add(meta.url)
                for ref in meta.refs:
                    if ref not in closure:
                        closure.add(ref)
                        pending.append(ref)
                if on_narinfo and not abort.is_set():
                    on_narinfo(meta)

        if abort.is_set():
            for remaining in in_flight:
                remaining.cancel()
            return None

    return closure, closure_nar


class NarDownloader:
    """Bounded worker coordinator for downloading unique NAR files."""

    def __init__(self, upstream: str, pool: ThreadPoolExecutor) -> None:
        self.upstream = upstream
        self.pool = pool
        self.slots = threading.Semaphore(DOWNLOAD_QUEUE)
        self.stop_event = threading.Event()
        self.state_lock = threading.Lock()
        self.queued_nars: set[str] = set()
        self.futures: list[Future[None]] = []
        self.downloaded = 0
        self.failed = False

    def enqueue(self, meta: NarInfoMeta) -> None:
        with self.state_lock:
            if meta.url in self.queued_nars or self.stop_event.is_set():
                return
            self.queued_nars.add(meta.url)

        with nar_lock:
            if meta.url in verified_nars:
                return

        dest = working_dir / STORE_DIR / meta.url
        if dest.is_file() and (
            meta.file_size is None or dest.stat().st_size == meta.file_size
        ):
            with nar_lock:
                verified_nars.add(meta.url)
            return

        while not self.stop_event.is_set():
            if not self.slots.acquire(timeout=0.5):
                continue
            try:
                fut = self.pool.submit(self._download_one, meta)
            except Exception:
                self.slots.release()
                raise
            self.futures.append(fut)
            return

    def _download_one(self, meta: NarInfoMeta) -> None:
        try:
            if self.stop_event.is_set():
                return
            download(
                f"{self.upstream}/{meta.url}",
                working_dir / STORE_DIR / meta.url,
                expected_size=meta.file_size,
                expected_hash=meta.file_hash,
            )
            with nar_lock:
                verified_nars.add(meta.url)
            with self.state_lock:
                self.downloaded += 1
                count = self.downloaded
                total = len(self.queued_nars)
            logger.info(f"    - [{count}/{total}] {meta.url}")
        except WORKER_ERRORS as e:
            logger.error(f"    - Failed to download {meta.url}: {e}")
            with self.state_lock:
                self.failed = True
            self.stop_event.set()
        finally:
            self.slots.release()

    def wait_all(self) -> None:
        for fut in self.futures:
            fut.result()


def read_channel_upstream(channel_dir: Path) -> str:
    return (channel_dir / ".original-binary-cache-url").read_text().strip().rstrip("/")


def sync_cache_info(channels: list[str]) -> bool:
    upstreams = list(
        dict.fromkeys(
            read_channel_upstream(working_dir / f".{channel}.update")
            for channel in channels
        )
    )
    dest = working_dir / STORE_DIR / "nix-cache-info"
    logger.info("  - Downloading nix-cache-info")
    for upstream in upstreams:
        try:
            download(f"{upstream}/nix-cache-info", dest)
            return True
        except WORKER_ERRORS as e:
            logger.warning(
                f"    - Failed to download nix-cache-info from {upstream}: {e}"
            )
    if dest.is_file() and dest.stat().st_size > 0:
        logger.warning("    - Using existing nix-cache-info after download failure")
        return True
    logger.error("    - No nix-cache-info available; aborting binary cache update")
    return False


def sync_channel_store(channel: str) -> bool:
    logger.info(f"  - {channel}")
    chan_path = working_dir / channel
    chan_update = working_dir / f".{channel}.update"
    upstream = read_channel_upstream(chan_update)

    roots, _ = read_store_root_hashes(chan_update / "store-paths.xz")
    logger.info(f"    - {len(roots)} paths listed")
    ok = True

    if roots:
        with ThreadPoolExecutor(max_workers=THREADS) as pool:
            downloader = NarDownloader(upstream, pool)
            closure_res = walk_closure(
                roots,
                upstream=upstream,
                on_narinfo=downloader.enqueue,
                stop_event=downloader.stop_event,
            )
            downloader.wait_all()

        ok = closure_res is not None and not downloader.failed
        resolved = len(closure_res[0]) if closure_res is not None else 0
        logger.info(
            f"    - {resolved} closure paths resolved, "
            f"{len(downloader.queued_nars)} unique NARs "
            f"({downloader.downloaded} downloaded)"
        )

    if ok:
        chan_update.rename(chan_path)
        logger.info("    - Finished with success, symlink updated")
    else:
        logger.info("    - Finished with errors, not updating symlink")
    return ok


def update_channels(channels: list[str]) -> bool:
    logger.info("- Updating binary cache")
    if not channels:
        return True
    if not sync_cache_info(channels):
        return False
    all_ok = True
    for channel in channels:
        if not sync_channel_store(channel):
            all_ok = False
    return all_ok


def garbage_collect() -> None:
    logger.info("- Collecting garbage")
    threshold = datetime.now(UTC) - timedelta(days=RETAIN_DAYS)
    last_updated: dict[str, datetime] = {}
    latest: dict[str, Path] = {}
    alive: set[Path] = set()

    for release in (working_dir / RELEASES_DIR).iterdir():
        if not (release / "binary-cache-url").exists():
            continue
        date_str = (release / ".released-time").read_text()
        date_match = re.match(r"\d+-\d+-\d+ \d+:\d+:\d+", date_str)
        assert date_match is not None, (
            f"Release {release!r} has invalid time {date_str!r}"
        )
        released = datetime.strptime(date_match[0], "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=UTC
        )
        if released < CLONE_SINCE:
            continue
        if released >= threshold:
            alive.add(release)
        channel = release.name.split("@")[0]
        if channel not in last_updated or last_updated[channel] < released:
            last_updated[channel] = released
            latest[channel] = release

    alive.update(latest.values())
    logger.info(f"  - {len(alive)} releases alive")

    roots: dict[str, None] = {}
    for release in alive:
        try:
            rel_roots, had_raw = read_store_root_hashes(release / "store-paths.xz")
        except (OSError, lzma.LZMAError, EOFError, ValueError) as e:
            logger.warning(f"Cannot read store paths for {release}; skipping GC: {e}")
            return
        if had_raw and not rel_roots:
            logger.warning(
                f"Cannot compute retained closure for {release}; skipping GC"
            )
            return
        roots.update(dict.fromkeys(rel_roots))

    res = walk_closure(list(roots))
    if res is None:
        return
    closure, closure_nar = res
    logger.info(f"  - {len(closure)} narinfo files in closure")
    logger.info(f"  - {len(closure_nar)} nar files in closure")

    deleted_ni = 0
    for path in (working_dir / STORE_DIR).iterdir():
        if not path.name.endswith(".narinfo"):
            continue
        key = path.name.removesuffix(".narinfo")
        if key in closure:
            continue
        deleted_ni += 1
        if DELETE_OLD:
            try:
                path.unlink()
                with narinfo_lock:
                    narinfo_cache.pop(key, None)
            except OSError as e:
                logger.warning(f"Failed to delete {path}: {e}")

    deleted_nar = 0
    for path in (working_dir / STORE_DIR / "nar").iterdir():
        nar_rel = f"nar/{path.name}"
        if nar_rel in closure_nar:
            continue
        deleted_nar += 1
        if DELETE_OLD:
            try:
                path.unlink()
                with nar_lock:
                    verified_nars.discard(nar_rel)
            except OSError as e:
                logger.warning(f"Failed to delete {path}: {e}")

    status = "deleted" if DELETE_OLD else "unreachable"
    logger.info(f"  - {deleted_ni} narinfo files {status}")
    logger.info(f"  - {deleted_nar} nar files {status}")


def main() -> int:
    (working_dir / RELEASES_DIR).mkdir(parents=True, exist_ok=True)
    (working_dir / STORE_DIR / "nar").mkdir(parents=True, exist_ok=True)
    garbage_collect()
    channels, clone_ok = clone_channels()
    update_ok = update_channels(channels)
    return 0 if clone_ok and update_ok else 1


if __name__ == "__main__":
    sys.exit(main())
