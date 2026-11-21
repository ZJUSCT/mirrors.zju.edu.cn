import logging
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path

import httpx2
from bs4 import BeautifulSoup

from .config import (
    RELEASES_DIR,
    SyncConfig,
    atomic_symlink,
    atomic_write_text,
    file_sha256,
)
from .http import WORKER_ERRORS, download, get_header, get_text

S3_CHANNELS_BUCKET_URL = "https://nix-channels.s3.amazonaws.com"
CHANNEL_NAME_RE = re.compile(r"(nixos|nixpkgs)-[^/]+")
TAGLINE_RE = re.compile(r"^Released on (.+?) (?:UTC )?from")

logger = logging.getLogger(__name__)


class ChannelStatus(StrEnum):
    UNCHANGED = "unchanged"
    STAGED = "staged"
    SKIPPED = "skipped"
    FAILED = "failed"


def parse_channel_page(html: str) -> tuple[str, list[tuple[str, str]]] | None:
    """Parse release timestamp and file (name, sha256) rows from a channel index."""
    soup = BeautifulSoup(html, "html.parser")
    tagline = " ".join(
        text for p in soup.find_all("p") if (text := " ".join(p.get_text().split()))
    )
    tagline_match = TAGLINE_RE.match(tagline)
    if tagline_match is None:
        logger.warning("Invalid channel tagline: %s", tagline)
        return None
    released_time = tagline_match[1]

    files = [
        (cells[0].get_text(strip=True), cells[2].get_text(strip=True))
        for tr in soup.find_all("tr")
        if len(cells := tr.find_all("td")) == 3
    ]
    return released_time, files


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
) -> None:
    for file_name, file_hash in files:
        if file_name.endswith((".ova", ".iso")):
            continue
        is_bcu = file_name == "binary-cache-url"
        dest_path = release_path / (
            ".original-binary-cache-url" if is_bcu else file_name
        )
        if dest_path.exists() and file_sha256(dest_path) == file_hash:
            logger.debug("%s: skipping existing %s", release_path.name, file_name)
            continue
        logger.info(
            "%s: downloading %s",
            release_path.name,
            "binary-cache-url (redirected)" if is_bcu else file_name,
        )
        await download(
            client,
            f"{chan_location}/{file_name}",
            dest_path,
            expected_sha256=file_hash,
        )


async def sync_channel(
    channel: str, cfg: SyncConfig, client: httpx2.AsyncClient
) -> ChannelStatus:
    chan_location = await get_header(
        client,
        f"{S3_CHANNELS_BUCKET_URL}/{channel}",
        "x-amz-website-redirect-location",
    )
    chan_release = chan_location.split("/")[-1]
    release_target = Path(RELEASES_DIR) / f"{channel}@{chan_release}"

    chan_path = cfg.working_dir / channel
    if chan_path.is_symlink() and chan_path.readlink() == release_target:
        return ChannelStatus.UNCHANGED

    logger.info("%s: syncing %s", channel, chan_release)
    try:
        html = await get_text(client, chan_location)
    except httpx2.HTTPStatusError as e:
        if e.response.status_code != 404:
            raise
        logger.warning("%s: skipped: release index not found", channel)
        return ChannelStatus.SKIPPED
    if (release_meta := parse_channel_page(html)) is None:
        logger.warning("%s: skipped: invalid release index", channel)
        return ChannelStatus.SKIPPED
    released_time, files = release_meta

    release_path = cfg.working_dir / release_target
    release_path.mkdir(parents=True, exist_ok=True)
    atomic_write_text(release_path / ".released-time", released_time)

    await sync_release_files(chan_location, release_path, files, client)

    atomic_symlink(cfg.working_dir / f".{channel}.update", release_target)
    logger.info("%s: staged %s", channel, chan_release)
    return ChannelStatus.STAGED


async def sync_channels(
    cfg: SyncConfig, client: httpx2.AsyncClient
) -> dict[str, ChannelStatus]:
    logger.info("Fetching channels")
    clone_since = datetime.now(UTC) - timedelta(days=cfg.clone_since_days)
    results: dict[str, ChannelStatus] = {}
    for channel, modified in await list_s3_channels(client):
        if modified < clone_since:
            continue
        try:
            results[channel] = await sync_channel(channel, cfg, client)
        except WORKER_ERRORS as e:
            logger.error("%s: sync failed: %r", channel, e)
            results[channel] = ChannelStatus.FAILED

    counts = Counter(results.values())
    summary = ", ".join(f"{status.value}={counts[status]}" for status in ChannelStatus)
    logger.info("Channel preparation complete: %s", summary)
    return results
