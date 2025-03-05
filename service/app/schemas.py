import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class OrderStatus(str, Enum):
    CREATED: str = "CREATED"
    PENDING: str = "PENDING"
    EXECUTED: str = "EXECUTED"
    FAILED: str = "FAILED"
    ERROR: str = "ERROR"


class OrderType(str, Enum):
    BUY: str = "BUY"
    SELL: str = "SELL"


class OrderCreate(BaseModel):
    order_type: OrderType
    price: float
    volume: float
    jetton_address: Optional[str] = None


class OrderUpdate(BaseModel):
    order_type: Optional[OrderType] = None
    price: Optional[float] = None
    volume: Optional[float] = None
    jetton_address: Optional[str] = None


class OrderResponse(BaseModel):
    order_id: str
    order_type: str
    price: float
    volume: float
    timestamp: datetime.datetime
    status: str
    tx_hash: Optional[str] = None
    wallet_id: int
    jetton_address: Optional[str] = None

    class Config:
        orm_mode = True
