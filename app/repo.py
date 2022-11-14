import time

from typing import List, Dict, AsyncContextManager, Optional, Tuple
from contextlib import asynccontextmanager

import asyncpg

from models import Metric, Asset


class AssetsRepo:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    @asynccontextmanager
    async def connection(self) -> AsyncContextManager[asyncpg.Connection]:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    async def exists(self, asset_id: int) -> bool:
        sql = 'select exists(select 1 from assets where id = $1)'
        async with self.connection() as conn:
            exists = await conn.fetchval(sql, asset_id)

        return exists

    async def get_by_name(self, name: str) -> Asset:
        sql = 'select id from assets where name = $1'
        async with self.connection() as conn:
            row = await conn.fetchrow(sql, name)

        if row:
            return Asset(id=row['id'], name=name)

    async def get_assets_list(self) -> List[Dict[int, str]]:
        sql = 'select id, name from assets;'
        async with self.connection() as conn:
            rows = await conn.fetch(sql)

        if rows:
            return [Asset(**row) for row in rows]

    async def get_asset_history(self, asset_id: int, history_minutes: int = 30) -> List[Metric]:
        sql = f'''
        select
          m.asset_id as "assetId",
          m.value,
          m.time,
          a.name as "assetName"
        from metrics m
        join assets a on a.id = m.asset_id
        where
          m.asset_id = $1
          and m.time > ($2 - ({history_minutes} * 60))
        order by m.time
        '''

        async with self.connection() as conn:
            rows = await conn.fetch(sql, asset_id, round(time.time()))

        if rows:
            return [Metric(**row) for row in rows]

        return []

    async def get_last_asset_metric(self, asset_id: int) -> Optional[Metric]:
        sql = f'''
        select
          m.asset_id as "assetId",
          m.value,
          m.time,
          a.name as "assetName"
        from metrics m
        join assets a on a.id = m.asset_id
        where m.asset_id = $1
        order by m.time desc limit 1;
        '''

        async with self.connection() as conn:
            row = await conn.fetchrow(sql, asset_id)

        if row:
            return Metric(**row)

    async def save_metrics(self, metrics: List[Tuple]) -> None:
        sql = 'insert into metrics (asset_id, value, time) values ($1, $2, $3);'
        async with self.connection() as conn:
            await conn.executemany(sql, metrics)
