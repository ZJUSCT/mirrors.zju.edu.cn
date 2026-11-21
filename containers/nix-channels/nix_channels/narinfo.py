import hashlib
import logging
import os
import pickle
import sys
import time
from compression import bz2, gzip, lzma, zlib, zstd
from pathlib import Path
from typing import NamedTuple, NoReturn, Self

from .config import STORE_DIR, NarUrl, StoreHash, VerificationError, atomic_path

NARINFO_INDEX_FILE = ".narinfo-index.pkl"
NARINFO_INDEX_VERSION = 1
NARINFO_INDEX_PROTOCOL = 5
NIX32_ALPHABET = "0123456789abcdfghijklmnpqrsvwxyz"

NAR_OPENERS = {
    "none": Path.open,
    "zstd": zstd.open,
    "xz": lzma.open,
    "bzip2": bz2.open,
    "gzip": gzip.open,
}
DECOMPRESS_ERRORS = (zstd.ZstdError, lzma.LZMAError, zlib.error, EOFError, OSError)

logger = logging.getLogger(__name__)


def hash_part(path: str) -> str:
    return sys.intern(path.split("/")[-1].split("-", 1)[0])


def to_nix32(digest: bytes) -> str:
    n = int.from_bytes(digest, "little")
    length = (len(digest) * 8 + 4) // 5
    return "".join(
        NIX32_ALPHABET[(n >> (5 * i)) & 0x1F] for i in range(length - 1, -1, -1)
    )


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
        fields = dict(line.split(": ", 1) for line in text.splitlines() if line)

        if not (raw_url := fields.get("URL")):
            raise ValueError("Missing URL in narinfo")

        compression = fields.get("Compression") or "bzip2"
        if compression not in NAR_OPENERS:
            raise ValueError(f"Unsupported Compression {compression!r} in narinfo")

        return cls(
            url=NarUrl(raw_url),
            compression=sys.intern(compression),
            file_size=int(fields["FileSize"]),
            file_hash=fields["FileHash"],
            nar_size=int(fields["NarSize"]),
            nar_hash=fields["NarHash"],
            refs=tuple(
                StoreHash(hash_part(ref))
                for ref in fields.get("References", "").split()
            ),
        )


class _RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str) -> NoReturn:
        raise pickle.UnpicklingError(f"Forbidden global {module}.{name}")


class NarInfoCache(dict[StoreHash, NarInfo]):
    """In-memory .narinfo cache tracking whether the on-disk index needs saving."""

    dirty: bool = False

    def set(self, key: StoreHash, value: NarInfo) -> None:
        if self.get(key) != value:
            self[key] = value
            self.dirty = True

    def remove(self, key: StoreHash) -> None:
        if self.pop(key, None) is not None:
            self.dirty = True

    def prune_missing(self, present: set[StoreHash]) -> None:
        if stale := self.keys() - present:
            for key in stale:
                del self[key]
            self.dirty = True

    @classmethod
    def load(cls, working_dir: Path, present: set[StoreHash]) -> Self:
        cache = cls()
        index_path = working_dir / NARINFO_INDEX_FILE
        if not index_path.is_file():
            logger.info("No local narinfo index found; will build from disk")
            return cache

        t0 = time.monotonic()
        stale = 0
        try:
            with index_path.open("rb", buffering=1 << 20) as f:
                payload = _RestrictedUnpickler(f).load()
            if (
                not isinstance(payload, tuple)
                or len(payload) != 2
                or payload[0] != NARINFO_INDEX_VERSION
                or not isinstance(payload[1], dict)
            ):
                logger.warning("Unexpected index format in %s; rebuilding", index_path)
                cache.dirty = True
                return cache

            make_narinfo = NarInfo._make
            field_count = len(NarInfo._fields)
            for store_hash, row in payload[1].items():
                if (
                    not isinstance(store_hash, str)
                    or not isinstance(row, tuple)
                    or len(row) != field_count
                    or not isinstance(row[6], tuple)
                ):
                    raise ValueError("Invalid narinfo index entry")
                if store_hash not in present:
                    stale += 1
                    continue
                cache[StoreHash(store_hash)] = make_narinfo(row)
        except (OSError, EOFError, pickle.UnpicklingError, TypeError, ValueError) as e:
            logger.warning(
                "Failed to load narinfo index %s; rebuilding: %r", index_path, e
            )
            cache.clear()
            cache.dirty = True
            return cache

        cache.dirty = stale > 0
        dt = time.monotonic() - t0
        logger.info(
            "Loaded %d narinfo index entries (%d stale) in %.1fs",
            len(cache),
            stale,
            dt,
        )
        return cache

    def save(self, working_dir: Path) -> None:
        if not self.dirty:
            return
        t0 = time.monotonic()
        index_path = working_dir / NARINFO_INDEX_FILE
        try:
            with (
                atomic_path(index_path) as tmp,
                tmp.open("wb", buffering=1 << 20) as f,
            ):
                pickle.dump(
                    (
                        NARINFO_INDEX_VERSION,
                        {store_hash: tuple(meta) for store_hash, meta in self.items()},
                    ),
                    f,
                    protocol=NARINFO_INDEX_PROTOCOL,
                )
                f.flush()
                os.fsync(f.fileno())
            self.dirty = False
            dt = time.monotonic() - t0
            logger.info("Saved %d narinfo index entries in %.1fs", len(self), dt)
        except OSError as e:
            logger.warning("Failed to save narinfo index %s: %r", index_path, e)


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
    with lzma.open(xz_path, "rt", encoding="utf-8") as f:
        return list(
            dict.fromkeys(
                StoreHash(hash_part(path)) for line in f if (path := line.rstrip())
            )
        )


def scan_store_dir(store_dir: Path) -> set[StoreHash]:
    """Return present store .narinfo hashes in store_dir."""
    if not store_dir.is_dir():
        return set()
    intern = sys.intern
    with os.scandir(store_dir) as it:
        return {
            StoreHash(intern(entry.name.removesuffix(".narinfo")))
            for entry in it
            if entry.name.endswith(".narinfo") and entry.is_file(follow_symlinks=False)
        }


def read_narinfo_file(hash_key: StoreHash, working_dir: Path) -> NarInfo:
    path = working_dir / STORE_DIR / f"{hash_key}.narinfo"
    return NarInfo.parse(path.read_text(encoding="utf-8"))
