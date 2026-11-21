import asyncio
import hashlib
import logging
from pathlib import Path

import httpx2
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from .config import VerificationError, atomic_path
from .narinfo import NarInfo, to_nix32, verify_nar_file

MAX_RETRIES = 5
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
WORKER_ERRORS = (OSError, ValueError, httpx2.HTTPError, VerificationError)

logger = logging.getLogger(__name__)


def is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, httpx2.RequestError | VerificationError) or (
        isinstance(exc, httpx2.HTTPStatusError)
        and exc.response.status_code in RETRYABLE_STATUS_CODES
    )


def log_retry(state: RetryCallState) -> None:
    exc = state.outcome.exception() if state.outcome else None
    url = state.kwargs.get("url") or (state.args[1] if len(state.args) > 1 else "?")
    logger.warning(
        "Retrying (%d/%d) in %.0fs for %s: %r",
        state.attempt_number,
        MAX_RETRIES,
        state.upcoming_sleep,
        url,
        exc,
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
    with atomic_path(dest) as tmp:
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
