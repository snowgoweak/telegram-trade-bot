import datetime
import uuid
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from service.app.database import get_db
from service.app.models import Order, User, Wallet

router = APIRouter()


class OrderType(str, Enum):
    TON_TO_JETTON: str = "TON_TO_JETTON"
    JETTON_TO_TON: str = "JETTON_TO_TON"


class OrderCreate(BaseModel):
    order_type: OrderType
    price: float
    volume: float
    jetton_address: Optional[str] = None


class OrderUpdate(BaseModel):
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


@router.post("/orders/{telegram_user_id}", response_model=OrderResponse)
async def create_order(
    telegram_user_id: str, order_data: OrderCreate, db: AsyncSession = Depends(get_db)
):
    """
    Создание ордера:
    1. Находим пользователя по telegram_user_id.
    2. Получаем кошелек пользователя.
    3. Создаем ордер, привязываем его к кошельку.
    """
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = wallet_result.scalars().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Кошелек не найден")

    new_order = Order(
        order_id=str(uuid.uuid4()),
        order_type=order_data.order_type,
        price=order_data.price,
        volume=order_data.volume,
        jetton_address=order_data.jetton_address,
        wallet_id=wallet.id,
        status="created",
        timestamp=datetime.datetime.utcnow(),
    )
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)
    return new_order


@router.get("/orders/{telegram_user_id}", response_model=List[OrderResponse])
async def get_orders(telegram_user_id: str, db: AsyncSession = Depends(get_db)):
    """
    Получение списка ордеров для пользователя.
    """
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = wallet_result.scalars().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Кошелек не найден")

    orders_result = await db.execute(select(Order).where(Order.wallet_id == wallet.id))
    orders = orders_result.scalars().all()
    return orders


@router.get("/orders/{telegram_user_id}/{order_id}", response_model=OrderResponse)
async def get_order(
    telegram_user_id: str, order_id: str, db: AsyncSession = Depends(get_db)
):
    """
    Получение информации об ордере по order_id для пользователя.
    """
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = wallet_result.scalars().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Кошелек не найден")

    order_result = await db.execute(
        select(Order).where(Order.order_id == order_id, Order.wallet_id == wallet.id)
    )
    order = order_result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Ордер не найден")
    return order


@router.delete("/orders/{telegram_user_id}/{order_id}")
async def delete_order(
    telegram_user_id: str, order_id: str, db: AsyncSession = Depends(get_db)
):
    """
    Удаление ордера:
    Если ордер находится в состоянии "pending", удаляем его (либо можно пометить как cancelled).
    """
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = wallet_result.scalars().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Кошелек не найден")

    order_result = await db.execute(
        select(Order).where(Order.order_id == order_id, Order.wallet_id == wallet.id)
    )
    order = order_result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Ордер не найден")

    if order.status != "created":
        raise HTTPException(status_code=400, detail="Ордер нельзя удалить")
    await db.delete(order)
    await db.commit()
    return {"detail": "Ордер удалён"}


@router.put("/orders/{telegram_user_id}/{order_id}")
async def update_order(
    telegram_user_id: str,
    order_id: str,
    order_update: OrderUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Ручка для редактирования ордера.
    1. Находим пользователя и его кошелек.
    2. Ищем ордер по order_id, связанный с кошельком.
    3. Если ордер находится в состоянии "pending", обновляем указанные поля.
    4. Если ордер не pending, редактирование запрещено.
    """
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = wallet_result.scalars().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Кошелек не найден")

    order_result = await db.execute(
        select(Order).where(Order.order_id == order_id, Order.wallet_id == wallet.id)
    )
    order = order_result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Ордер не найден")

    if order.status != "created":
        raise HTTPException(
            status_code=400,
            detail="Редактирование ордера невозможно, статус ордера не 'created'",
        )

    if order_update.price is not None:
        order.price = order_update.price
    if order_update.volume is not None:
        order.volume = order_update.volume
    if order_update.jetton_address is not None:
        order.jetton_address = order_update.jetton_address

    await db.commit()
    await db.refresh(order)
    return {"detail": "Ордер обновлён", "order": order}
