import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.config import settings
from bot.keyboards import (
    get_main_menu_keyboard,
    get_order_detail_keyboard,
    get_orders_menu_keyboard,
)

# Новые состояния для обновления ордера (начинаются с 100)
UPDATE_TYPE, UPDATE_PRICE, UPDATE_VOLUME, UPDATE_JETTON = range(100, 104)


def get_update_order_type_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для обновления типа ордера:
    - Buy, Sell и кнопка "Пропустить", чтобы оставить текущий тип.
    """
    keyboard = [
        [
            InlineKeyboardButton(text="Buy", callback_data="update_order_type_buy"),
            InlineKeyboardButton(text="Sell", callback_data="update_order_type_sell"),
            InlineKeyboardButton(
                text="Пропустить", callback_data="update_order_type_skip"
            ),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def update_order_start(update: Update, context: CallbackContext) -> int:
    """
    Точка входа в обновление ордера.
    Извлекает order_id из callback_data (формат "order_update_<order_id>"),
    получает текущие данные ордера и переходит к шагу обновления типа.
    """
    query = update.callback_query
    await query.answer()
    data = query.data
    order_id = data.split("_", 2)[-1]
    context.user_data["order_id"] = order_id
    telegram_user_id = str(query.from_user.id)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SERVICE_URL}/api/orders/{telegram_user_id}/{order_id}"
            )
            response.raise_for_status()
            order_data = response.json()
        context.user_data["current_order"] = order_data
    except Exception as e:
        await query.edit_message_text(
            text=f"Ошибка при получении текущих данных ордера: {str(e)}",
            reply_markup=get_orders_menu_keyboard(),
        )
        return ConversationHandler.END

    current_type = context.user_data["current_order"].get("order_type")
    text = (
        f"Обновление ордера {order_id}\n"
        f"Текущий тип ордера: {current_type}\n"
        "Выберите новый тип ордера или нажмите «Пропустить», чтобы оставить текущий."
    )
    await query.edit_message_text(
        text=text, reply_markup=get_update_order_type_keyboard()
    )
    return UPDATE_TYPE


async def update_order_type_callback(update: Update, context: CallbackContext) -> int:
    """
    Обработка выбора нового типа ордера.
    Если пользователь нажал «Пропустить», оставляется текущий тип.
    Затем запрашивается ввод новой цены.
    """
    query = update.callback_query
    await query.answer()
    data = query.data
    current_type = context.user_data["current_order"].get("order_type")
    if data == "update_order_type_buy":
        new_type = "BUY"
    elif data == "update_order_type_sell":
        new_type = "SELL"
    elif data == "update_order_type_skip":
        new_type = current_type
    else:
        new_type = current_type
    context.user_data["new_type"] = new_type

    current_price = context.user_data["current_order"].get("price")
    text = (
        f"Текущий тип ордера: {current_type}\n"
        f"Новый тип ордера: {new_type}\n"
        f"Текущая цена: {current_price}\n"
        "Введите новую цену или отправьте /skip, чтобы оставить текущую цену."
    )
    await query.edit_message_text(text=text)
    return UPDATE_PRICE


async def update_order_price(update: Update, context: CallbackContext) -> int:
    """
    Обрабатывает ввод новой цены.
    Если введено /skip, сохраняется текущая цена.
    Затем запрашивается новый объём.
    """
    text = update.message.text.strip()
    current_price = context.user_data["current_order"].get("price")
    if text == "/skip":
        new_price = current_price
    else:
        try:
            new_price = float(text)
        except ValueError:
            await update.message.reply_text(
                "Цена должна быть числом. Введите новую цену или /skip:"
            )
            return UPDATE_PRICE
    context.user_data["new_price"] = new_price
    current_volume = context.user_data["current_order"].get("volume")
    await update.message.reply_text(
        f"Текущий объём: {current_volume}\nВведите новый объём или отправьте /skip для сохранения текущего объёма."
    )
    return UPDATE_VOLUME


async def update_order_volume(update: Update, context: CallbackContext) -> int:
    """
    Обрабатывает ввод нового объёма.
    Если введено /skip, сохраняется текущий объём.
    Затем запрашивается новый адрес jetton.
    """
    text = update.message.text.strip()
    current_volume = context.user_data["current_order"].get("volume")
    if text == "/skip":
        new_volume = current_volume
    else:
        try:
            new_volume = float(text)
        except ValueError:
            await update.message.reply_text(
                "Объём должен быть числом. Введите новый объём или /skip:"
            )
            return UPDATE_VOLUME
    context.user_data["new_volume"] = new_volume
    current_jetton = (
        context.user_data["current_order"].get("jetton_address") or "не указан"
    )
    await update.message.reply_text(
        f"Текущий адрес jetton: {current_jetton}\nВведите новый адрес или отправьте /skip для сохранения текущего."
    )
    return UPDATE_JETTON


async def update_order_jetton(update: Update, context: CallbackContext) -> int:
    """
    Обрабатывает ввод нового адреса jetton.
    Если введено /skip, сохраняется текущее значение.
    Затем отправляется PUT‑запрос на обновление ордера.
    """
    text = update.message.text.strip()
    current_jetton = context.user_data["current_order"].get("jetton_address")
    if text == "/skip":
        new_jetton = current_jetton
    else:
        new_jetton = text
    context.user_data["new_jetton"] = new_jetton

    order_id = context.user_data["order_id"]
    telegram_user_id = str(update.effective_user.id)
    update_data = {
        "order_type": context.user_data["new_type"],
        "price": context.user_data["new_price"],
        "volume": context.user_data["new_volume"],
        "jetton_address": context.user_data["new_jetton"],
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{settings.SERVICE_URL}/api/orders/{telegram_user_id}/{order_id}",
                json=update_data,
            )
            response.raise_for_status()
            result = response.json()
        updated_order = result.get("order")
        text = (
            f"Ордер обновлён успешно!\n"
            f"ID: {updated_order.get('order_id')}\n"
            f"Тип: {updated_order.get('order_type')}\n"
            f"Новая цена: {updated_order.get('price')}\n"
            f"Новый объём: {updated_order.get('volume')}\n"
            f"Новый адрес jetton: {updated_order.get('jetton_address')}"
        )
    except Exception as e:
        text = f"Ошибка при обновлении ордера: {str(e)}"
    await update.message.reply_text(text, reply_markup=get_orders_menu_keyboard())
    return ConversationHandler.END


async def update_order_cancel(update: Update, context: CallbackContext) -> int:
    """
    Обработчик отмены обновления ордера.
    """
    await update.message.reply_text(
        "Обновление ордера отменено.", reply_markup=get_orders_menu_keyboard()
    )
    return ConversationHandler.END
