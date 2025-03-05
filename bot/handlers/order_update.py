import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
)

from bot.config import settings
from bot.keyboards import (
    get_orders_menu_keyboard,
)

# New states for order update (starting from 100)
UPDATE_TYPE, UPDATE_PRICE, UPDATE_VOLUME, UPDATE_JETTON = range(100, 104)


def get_update_order_type_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard for updating the order type:
    - Buy, Sell, and a "Skip" button to keep the current type.
    """
    keyboard = [
        [
            InlineKeyboardButton(text="Buy", callback_data="update_order_type_buy"),
            InlineKeyboardButton(text="Sell", callback_data="update_order_type_sell"),
            InlineKeyboardButton(text="Skip", callback_data="update_order_type_skip"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def update_order_start(update: Update, context: CallbackContext) -> int:
    """
    Entry point for updating an order.
    Extracts the order_id from callback_data (format "order_update_<order_id>"),
    retrieves the current order data, and proceeds to the order type update step.
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
            text=f"Error retrieving current order data: {str(e)}",
            reply_markup=get_orders_menu_keyboard(),
        )
        return ConversationHandler.END

    current_type = context.user_data["current_order"].get("order_type")
    text = (
        f"Updating order {order_id}\n"
        f"Current order type: {current_type}\n"
        "Select a new order type or press 'Skip' to keep the current type."
    )
    await query.edit_message_text(
        text=text, reply_markup=get_update_order_type_keyboard()
    )
    return UPDATE_TYPE


async def update_order_type_callback(update: Update, context: CallbackContext) -> int:
    """
    Handles the selection of a new order type.
    If the user pressed "Skip", the current type is retained.
    Then it prompts for a new price.
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
        f"Current order type: {current_type}\n"
        f"New order type: {new_type}\n"
        f"Current price: {current_price}\n"
        "Enter a new price or send /skip to keep the current price."
    )
    await query.edit_message_text(text=text)
    return UPDATE_PRICE


async def update_order_price(update: Update, context: CallbackContext) -> int:
    """
    Handles input of a new price.
    If /skip is entered, the current price is retained.
    Then it prompts for a new volume.
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
                "Price must be a number. Enter a new price or /skip:"
            )
            return UPDATE_PRICE
    context.user_data["new_price"] = new_price
    current_volume = context.user_data["current_order"].get("volume")
    await update.message.reply_text(
        f"Current volume: {current_volume}\nEnter a new volume or send /skip to keep the current volume."
    )
    return UPDATE_VOLUME


async def update_order_volume(update: Update, context: CallbackContext) -> int:
    """
    Handles input of a new volume.
    If /skip is entered, the current volume is retained.
    Then it prompts for a new jetton address.
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
                "Volume must be a number. Enter a new volume or /skip:"
            )
            return UPDATE_VOLUME
    context.user_data["new_volume"] = new_volume
    current_jetton = (
        context.user_data["current_order"].get("jetton_address") or "not specified"
    )
    await update.message.reply_text(
        f"Current jetton address: {current_jetton}\nEnter a new address or send /skip to keep the current one."
    )
    return UPDATE_JETTON


async def update_order_jetton(update: Update, context: CallbackContext) -> int:
    """
    Handles input of a new jetton address.
    If /skip is entered, the current address is retained.
    Then a PUT request is sent to update the order.
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
            f"Order updated successfully!\n"
            f"ID: {updated_order.get('order_id')}\n"
            f"Type: {updated_order.get('order_type')}\n"
            f"New price: {updated_order.get('price')}\n"
            f"New volume: {updated_order.get('volume')}\n"
            f"New jetton address: {updated_order.get('jetton_address')}"
        )
    except Exception as e:
        text = f"Error updating order: {str(e)}"
    await update.message.reply_text(text, reply_markup=get_orders_menu_keyboard())
    return ConversationHandler.END


async def update_order_cancel(update: Update, context: CallbackContext) -> int:
    """
    Handler for cancelling the order update.
    """
    await update.message.reply_text(
        "Order update cancelled.", reply_markup=get_orders_menu_keyboard()
    )
    return ConversationHandler.END
