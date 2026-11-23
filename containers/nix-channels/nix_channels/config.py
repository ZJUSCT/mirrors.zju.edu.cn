import hashlib
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import ClassVar, NewType

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

STORE_DIR = "store"
RELEASES_DIR = "releases"

StoreHash = NewType("StoreHash", str)
NarUrl = NewType("NarUrl", str)


class VerificationError(RuntimeError):
    """Raised when a downloaded or cached file fails size or hash verification."""


class AbortGCError(RuntimeError):
    """Raised when GC integrity checks fail and collection must abort."""


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


def file_sha256(dest: Path) -> str:
    with dest.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


@contextmanager
def atomic_path(dest: Path) -> Generator[Path]:
    tmp = dest.parent / f".{dest.name}.tmp"
    tmp.unlink(missing_ok=True)
    try:
        yield tmp
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    with atomic_path(path) as tmp:
        tmp.write_text(content, encoding=encoding)


def atomic_symlink(link: Path, target: str | Path) -> None:
    with atomic_path(link) as tmp:
        tmp.symlink_to(target)
