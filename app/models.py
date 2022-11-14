from enum import Enum
from typing import Dict, Any

from pydantic import BaseModel


class Action(str, Enum):
    assets = 'assets'
    asset_history = 'asset_history'
    subscribe = 'subscribe'


class Asset(BaseModel):
    id: int
    name: str


class Message(BaseModel):
    action: Action
    message: Dict[str, Any]


class Metric(BaseModel):
    assetId: int
    assetName: str
    time: int
    value: float
