import asyncio
import logging

from collections import defaultdict
from typing import Dict, Set

import asyncpg
import websockets

from fastapi import FastAPI, WebSocket

from subscriptions import Subscription, SubscriptionsManager
from exceptions import InvalidRequestException
from models import Action, Message, Metric
from repo import AssetsRepo
from settings import DB_DSN

logger = logging.getLogger(__name__)


async def get_client_message(websocket: WebSocket, queue: asyncio.Queue) -> Message:
    try:
        async for data in websocket.iter_json():
            await queue.put(Message(**data))
    except Exception as exc:
        logger.error(f'Invalid request. Error: {exc}', exc_info=True)
        raise InvalidRequestException


async def process_client_message(
    subs_manager: SubscriptionsManager, websocket: WebSocket, queue: asyncio.Queue
) -> None:
    while True:
        if queue.empty():
            await asyncio.sleep(0)
        else:
            client_message: Message = await queue.get()
            if client_message.action == Action.assets:
                data = await subs_manager.assets_repo.get_assets_list()
                msg = Message(action=Action.assets, message={'assets': data})
                await websocket.send_json(msg.dict())
            elif client_message.action == Action.subscribe:
                asset_id = int(client_message.message['assetId'])
                if websocket in subs_manager.subscribers and subs_manager.subscribers[websocket].asset_id != asset_id:
                    await subs_manager.resubscribe_client(websocket, asset_id)
                else:
                    await subs_manager.subscribe_client(websocket, asset_id)


app = FastAPI()


@app.on_event('startup')
async def start_subs_processing() -> None:
    pool = await asyncpg.create_pool(DB_DSN)
    app.assets_storage = AssetsRepo(pool)
    app.subs_manager = SubscriptionsManager(app.assets_storage)
    asyncio.create_task(app.subs_manager.process_subscriptions())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    queue = asyncio.Queue()
    logger.info(f'new client at: {websocket}')
    while True:
        try:
            await asyncio.gather(
                get_client_message(websocket, queue),
                process_client_message(websocket.app.subs_manager, websocket, queue),
            )
        except InvalidRequestException:
            return websocket
        except websockets.exceptions.ConnectionClosedError as exc:
            print(f'Client at websocket {websocket} have closed the connection')
            logger.info(f'Client at websocket {websocket} have closed the connection')
            return websocket
        except Exception as exc:
            logger.exception(f'Unknown error occurred {exc}', exc_info=True)
            return websocket


if __name__ == '__main__':
    import uvicorn

    # uvicorn.run("main:app", port=8080, log_level='info', reload=True, loop='uvloop', host='0.0.0.0')
    uvicorn.run("main:app", port=8080, log_level='info', loop='uvloop', host='0.0.0.0')
