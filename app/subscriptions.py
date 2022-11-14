import asyncio

from typing import Set, Dict
from collections import defaultdict

from fastapi import WebSocket

from repo import AssetsRepo
from models import Metric, Action


class Subscription:
    def __init__(self, client: WebSocket, asset_id: int) -> None:
        self.client = client
        self.asset_id = asset_id
        self.initialized = False

    async def send_metric(self, metric: Metric) -> None:
        await self.client.send_json(metric.dict())

    async def send_error_msg(self, msg: str) -> None:
        await self.client.send_text(msg)


class SubscriptionsManager:
    def __init__(self, assets_repo: AssetsRepo) -> None:
        self.assets_repo = assets_repo
        self.subscribers: Dict[WebSocket, Subscription] = {}
        self.subs_per_asset: Dict[int, Set[Subscription]] = defaultdict(set)
        self.disconnected_subscribers: Set[Subscription] = set()

    async def process_subscriptions(self) -> None:
        while True:
            if not self.subs_per_asset:
                await asyncio.sleep(1)
                continue

            for asset_id in self.subs_per_asset:
                metric = await self.assets_repo.get_last_asset_metric(asset_id)
                for subscription in self.subs_per_asset[asset_id]:
                    await self.process_subscription(asset_id, subscription, metric)

            self.remove_disconnected_clients()
            await asyncio.sleep(1)

    def remove_disconnected_clients(self) -> None:
        for sub in self.disconnected_subscribers:
            self.unsunscribe_client(sub)
        self.disconnected_subscribers.clear()

    async def process_subscription(self, asset_id: int, subscription: Subscription, metric: Metric) -> None:
        if subscription.client.client_state.value == 1:
            if not subscription.initialized:
                subscription.initialized = True
                history = await self.assets_repo.get_asset_history(asset_id)
                await subscription.client.send_json(
                    {'action': Action.asset_history, 'message': {'points': [point.dict() for point in history]}}
                )
            if metric is not None:
                await subscription.send_metric(metric)
        else:
            self.disconnected_subscribers.add(subscription)

    async def subscribe_client(self, websocket: WebSocket, asset_id: int) -> None:
        if not (await self.assets_repo.exists(asset_id)):
            return

        subscription = Subscription(client=websocket, asset_id=asset_id)
        self.subscribers[subscription.client] = subscription
        self.subs_per_asset[subscription.asset_id].add(subscription)

    def unsunscribe_client(self, subscription: Subscription) -> None:
        del self.subscribers[subscription.client]
        self.subs_per_asset[subscription.asset_id].remove(subscription)

    async def resubscribe_client(self, websocket: WebSocket, new_asset_id: int) -> None:
        self.unsunscribe_client(self.subscribers[websocket])
        await self.subscribe_client(websocket, new_asset_id)
