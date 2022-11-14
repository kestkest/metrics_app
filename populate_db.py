import asyncio

import asyncpg

import logging

from app.settings import DB_DSN

assets = (('EURUSD',), ('USDJPY',), ('GBPUSD',), ('AUDUSD',), ('USDCAD',))


async def save_assets() -> None:
    conn: asyncpg.Connection = await asyncpg.connect(DB_DSN)
    sql = 'insert into assets (name) values($1)'
    try:
        await conn.executemany(sql, assets)
    except Exception as exc:
        logging.exception(exc)
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(save_assets())
