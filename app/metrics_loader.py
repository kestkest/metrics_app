import logging
import json
import time
import asyncio
import random


from typing import List, Dict, Tuple

from asyncpg import create_pool
from aiohttp import ClientSession, TCPConnector

from repo import AssetsRepo
from settings import METRICS_URL, DB_DSN

logger = logging.getLogger(__name__)


class Loader:
    def __init__(self, repo: AssetsRepo) -> None:
        self.session = ClientSession(connector=TCPConnector(ttl_dns_cache=600, keepalive_timeout=10))
        self.repo = repo
        self.assets_list: List = None
        self.assets_map: Dict = None

    async def setup(self) -> None:
        await self.setup_assets()

    async def setup_assets(self) -> None:
        self.assets_list = await self.repo.get_assets_list()
        self.assets_map = {asset.name: asset.id for asset in self.assets_list}

    async def load(self) -> None:
        while True:
            try:
                start = time.time()
                if self.assets_map is not None:
                    metrics = await self.get_metrics()
                    prepared_metrics = await self.prepare_metrics(metrics)
                    await self.repo.save_metrics(prepared_metrics)
            except Exception as exc:
                logger.exception(f'{exc}')
                metrics = self.make_dummy_metrics()
                await self.repo.save_metrics(metrics)
            finally:
                await asyncio.sleep(1 - (time.time() - start))

    async def get_metrics(self) -> List[Dict]:
        async with self.session.get(METRICS_URL) as response:
            text = await response.text()
            body = json.loads(text[14:-4])

        return body

    async def prepare_metrics(self, metrics: List[Dict]) -> List[Tuple]:
        timestamp = int(time.time())
        return [
            (self.assets_map[m['Symbol']], (m['Bid'] + m['Ask']) / 2, timestamp)
            for m in metrics
            if m['Symbol'] in self.assets_map
        ]

    def make_dummy_metrics(self) -> List[Tuple]:
        timestamp = round(time.time())
        return [(self.assets_map[name], random.random(), timestamp) for name in self.assets_map]


async def main() -> None:
    pool = await create_pool(DB_DSN, min_size=1, max_size=3)
    loader = Loader(AssetsRepo(pool))
    await loader.setup()
    await loader.load()


if __name__ == '__main__':
    asyncio.run(main())
