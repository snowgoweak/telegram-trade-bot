import datetime
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from service.app.database import get_db
from service.app.models import Order, User, Wallet
from service.app.schemas import OrderCreate, OrderResponse, OrderStatus, OrderUpdate

router = APIRouter()


@router.post("/orders/{telegram_user_id}", response_model=OrderResponse)
async def create_order(
    telegram_user_id: str, order_data: OrderCreate, db: AsyncSession = Depends(get_db)
):

    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="The user was not found")

    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = wallet_result.scalars().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    new_order = Order(
        order_id=str(uuid.uuid4()),
        order_type=order_data.order_type,
        price=order_data.price,
        volume=order_data.volume,
        jetton_address=order_data.jetton_address,
        wallet_id=wallet.id,
        status=OrderStatus.CREATED.value,
        timestamp=datetime.datetime.utcnow(),
    )
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)
    return new_order


@router.get("/orders/{telegram_user_id}", response_model=List[OrderResponse])
async def get_orders(telegram_user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="The user was not found")

    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = wallet_result.scalars().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    orders_result = await db.execute(select(Order).where(Order.wallet_id == wallet.id))
    orders = orders_result.scalars().all()
    return orders


@router.get("/orders/{telegram_user_id}/{order_id}", response_model=OrderResponse)
async def get_order(
    telegram_user_id: str, order_id: str, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="The user was not found")

    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = wallet_result.scalars().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    order_result = await db.execute(
        select(Order).where(Order.order_id == order_id, Order.wallet_id == wallet.id)
    )
    order = order_result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="The order was not found")
    return order


@router.delete("/orders/{telegram_user_id}/{order_id}")
async def delete_order(
    telegram_user_id: str, order_id: str, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="The user was not found")

    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = wallet_result.scalars().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    order_result = await db.execute(
        select(Order).where(Order.order_id == order_id, Order.wallet_id == wallet.id)
    )
    order = order_result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="The order was not found")

    if order.status != OrderStatus.CREATED.value:
        raise HTTPException(status_code=400, detail="The order cannot be deleted")
    await db.delete(order)
    await db.commit()
    return {"detail": "The order has been deleted"}


@router.put("/orders/{telegram_user_id}/{order_id}")
async def update_order(
    telegram_user_id: str,
    order_id: str,
    order_update: OrderUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="The user was not found")

    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = wallet_result.scalars().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    order_result = await db.execute(
        select(Order).where(Order.order_id == order_id, Order.wallet_id == wallet.id)
    )
    order = order_result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="The order was not found")

    if order.status != OrderStatus.CREATED.value:
        raise HTTPException(
            status_code=400,
            detail="Order editing is not possible, the order status is not 'created'",
        )

    if order_update.price is not None:
        order.price = order_update.price
    if order_update.volume is not None:
        order.volume = order_update.volume
    if order_update.jetton_address is not None:
        order.jetton_address = order_update.jetton_address

    await db.commit()
    await db.refresh(order)
    return {"detail": "The order has been updated", "order": order}
