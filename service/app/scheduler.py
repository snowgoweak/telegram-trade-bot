import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.future import select

from service.app.database import async_session
from service.app.models import Order, Wallet
from service.app.routes.wallet import ton_client
from service.app.schemas import OrderStatus, OrderType

logger = logging.getLogger(__name__)


async def check_and_execute_orders():
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(Order.status == OrderStatus.CREATED.value)
        )
        orders = result.scalars().all()
        if not orders:
            logger.info("Нет ордеров для исполнения")
            return

        for order in orders:
            try:
                price_in_ton = await ton_client.get_current_price(
                    order.jetton_address, order.order_type, order.volume
                )
                logger.info(
                    f"Ордер {order.order_id}: текущая цена для {order.jetton_address} = {price_in_ton}, целевая цена = {order.price}"
                )
                if price_in_ton >= order.price:
                    wallet_result = await session.execute(
                        select(Wallet).where(Wallet.id == order.wallet_id)
                    )
                    wallet_record = wallet_result.scalars().first()
                    if not wallet_record:
                        logger.error(f"Не найден кошелек для ордера {order.order_id}")
                        continue

                    wallet_obj = await ton_client.restore_wallet(wallet_record)
                    if order.order_type == OrderType.BUY.value:
                        tx_result = await ton_client.swap_ton_to_jetton(
                            wallet_obj, order.volume, order.jetton_address
                        )
                    elif order.order_type == OrderType.SELL.value:
                        tx_result = await ton_client.swap_jetton_to_ton(
                            wallet_obj, order.volume, order.jetton_address
                        )
                    else:
                        logger.error(f"Неизвестный тип ордера: {order.order_type}")
                        continue

                    order.status = OrderStatus.PENDING.value
                    order.tx_hash = tx_result.get("tx_hash")
                    await session.commit()
                    logger.info(
                        f"Ордер {order.order_id} исполнен, tx_hash: {order.tx_hash}"
                    )
                else:
                    logger.info(
                        f"Ордер {order.order_id} не исполнен: текущая цена {price_in_ton} не достигла целевой {order.price}"
                    )
            except Exception as e:
                logger.error(f"Ошибка при исполнении ордера {order.order_id}: {e}")
                await session.commit()


async def monitor_transaction_status():
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(
                Order.tx_hash.isnot(None), Order.status.in_([OrderStatus.PENDING.value])
            )
        )
        orders = result.scalars().all()
        if not orders:
            logger.info("Нет ордеров с ожидающим статусом транзакции")
            return

        for order in orders:
            try:
                tx_status = await ton_client.check_transaction_status(order.tx_hash)
                logger.info(f"Статус транзакции ордера {order.order_id}: {tx_status}")
                order.status = tx_status
                await session.commit()
            except Exception as e:
                logger.error(
                    f"Ошибка проверки транзакции для ордера {order.order_id}: {str(e)}"
                )


async def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_and_execute_orders, "interval", seconds=1)
    scheduler.add_job(monitor_transaction_status, "interval", seconds=1)
    scheduler.start()
    return scheduler
