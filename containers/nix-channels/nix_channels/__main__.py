import asyncio
import logging
import sys
from concurrent.futures import ThreadPoolExecutor

import httpx2

from .channels import ChannelStatus, sync_channels
from .config import RELEASES_DIR, STORE_DIR, StoreHash, SyncConfig
from .gc import garbage_collect
from .narinfo import NarInfoCache, scan_store_dir
from .store import sync_stores


async def main() -> int:
    cfg = SyncConfig()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s [%(module)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("httpx2").setLevel(logging.WARNING)
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
            for channel, status in channel_results.items()
            if status is ChannelStatus.STAGED
        ]
        channels_ok = all(
            status is not ChannelStatus.FAILED for status in channel_results.values()
        )
        stores_ok = True
        cache: NarInfoCache | None = None
        present: set[StoreHash] | None = None
        if channels or cfg.delete_old:
            present = await asyncio.to_thread(
                scan_store_dir, cfg.working_dir / STORE_DIR
            )
            cache = await asyncio.to_thread(NarInfoCache.load, cfg.working_dir, present)
        if channels and cache is not None and present is not None:
            stores_ok = await sync_stores(
                channels, cfg, cache, present, client, query_client
            )
            await asyncio.to_thread(cache.save, cfg.working_dir)
    if cfg.delete_old and cache is not None:
        gc_ok = garbage_collect(cfg, cache, present=present)
        cache.save(cfg.working_dir)
    else:
        gc_ok = True
    return 0 if channels_ok and stores_ok and gc_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
