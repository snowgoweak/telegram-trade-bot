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
from bot.handlers.order_update import (
    UPDATE_JETTON,
    UPDATE_PRICE,
    UPDATE_TYPE,
    UPDATE_VOLUME,
    update_order_cancel,
    update_order_jetton,
    update_order_price,
    update_order_start,
    update_order_type_callback,
    update_order_volume,
)
from bot.keyboards import (
    get_main_menu_keyboard,
    get_order_detail_keyboard,
    get_orders_menu_keyboard,
)

# Conversation states for order creation
ORDER_TYPE, PRICE, VOLUME, JETTON_ADDRESS = range(4)


def get_order_type_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard for selecting the order type:
    - Buy (displayed as BUY)
    - Sell (displayed as SELL)
    """
    keyboard = [
        [
            InlineKeyboardButton(text="Buy", callback_data="order_type_buy"),
            InlineKeyboardButton(text="Sell", callback_data="order_type_sell"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# ---------------- Telegram Handlers ----------------


STATUS_EMOJIS = {
    "CREATED": "🆕",
    "PENDING": "⏳",
    "EXECUTED": "✅",
    "FAILED": "❌",
    "ERROR": "🚫",
}


async def orders_menu_handler(update: Update, context: CallbackContext) -> None:
    """
    Handler to display the list of orders with pagination and status emojis.
    """
    query = update.callback_query
    await query.answer()

    data = query.data
    page = 0
    if data != "menu_orders":
        try:
            page = int(data.split("_")[-1])
        except Exception:
            page = 0

    telegram_user_id = str(query.from_user.id)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SERVICE_URL}/api/orders/{telegram_user_id}"
            )
            response.raise_for_status()
            orders_data = response.json()

        total_orders = len(orders_data)
        orders_per_page = 5
        start = page * orders_per_page
        end = start + orders_per_page
        page_orders = orders_data[start:end]

        if total_orders == 0:
            text = "You currently have no orders."
            keyboard = [
                [InlineKeyboardButton("Create order", callback_data="order_create")],
                [InlineKeyboardButton("Back", callback_data="menu_back")],
            ]
        else:
            text = f"<b>Your orders (page {page + 1}):</b>\n"
            keyboard = []

            # Build buttons for orders on the current page
            for order in page_orders:
                status = order.get("status", "CREATED")
                emoji = STATUS_EMOJIS.get(status, "")
                button_text = f"{emoji} Type: {order.get('order_type')}, Price: {order.get('price')}"
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            text=button_text,
                            callback_data=f"order_detail_{order.get('order_id')}",
                        )
                    ]
                )

            # Pagination buttons
            pagination_buttons = []
            if page > 0:
                pagination_buttons.append(
                    InlineKeyboardButton(
                        "◀ Back", callback_data=f"menu_orders_{page - 1}"
                    )
                )
            if end < total_orders:
                pagination_buttons.append(
                    InlineKeyboardButton(
                        "Forward ▶", callback_data=f"menu_orders_{page + 1}"
                    )
                )
            if pagination_buttons:
                keyboard.insert(0, pagination_buttons)

            # "Create order" and "Back" buttons
            keyboard.append(
                [
                    InlineKeyboardButton("Create order", callback_data="order_create"),
                    InlineKeyboardButton("Back", callback_data="menu_back"),
                ]
            )

        markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=markup, parse_mode="HTML")
    except Exception as e:
        await query.edit_message_text(
            text=f"Error retrieving orders: {str(e)}",
            reply_markup=get_main_menu_keyboard(),
        )


# --- ConversationHandler for order creation ---


async def order_start(update: Update, _: CallbackContext) -> int:
    """
    Entry point for creating an order.
    Called when the "Create order" button (callback_data="order_create") is pressed.
    Sends a message with the keyboard to select the order type.
    """
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "Select the order type:", reply_markup=get_order_type_keyboard()
    )
    return ORDER_TYPE


async def order_type_callback(update: Update, context: CallbackContext) -> int:
    """
    Handles the selection of the order type via inline buttons.
    If the user selects "Buy", order_type is set to BUY, otherwise to SELL.
    """
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "order_type_buy":
        context.user_data["order_type"] = "BUY"
    elif data == "order_type_sell":
        context.user_data["order_type"] = "SELL"
    else:
        await query.message.edit_text(
            "Invalid selection. Please try again.",
            reply_markup=get_order_type_keyboard(),
        )
        return ORDER_TYPE
    await query.message.edit_text("Enter the order price in TON (number):")
    return PRICE


async def order_price_handler(update: Update, context: CallbackContext) -> int:
    try:
        price = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "The price must be a number. Please enter the price again:"
        )
        return PRICE
    context.user_data["price"] = price
    await update.message.reply_text("Enter the order volume (number):")
    return VOLUME


async def order_volume_handler(update: Update, context: CallbackContext) -> int:
    try:
        volume = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "The volume must be a number. Please enter the volume again:"
        )
        return VOLUME
    context.user_data["volume"] = volume
    await update.message.reply_text("Enter the jetton address:")
    return JETTON_ADDRESS


async def order_jetton_handler(update: Update, context: CallbackContext) -> int:
    jetton_address = update.message.text.strip()
    context.user_data["jetton_address"] = jetton_address

    telegram_user_id = str(update.effective_user.id)
    order_data = {
        "order_type": context.user_data["order_type"],
        "price": context.user_data["price"],
        "volume": context.user_data["volume"],
        "jetton_address": context.user_data["jetton_address"],
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SERVICE_URL}/api/orders/{telegram_user_id}", json=order_data
            )
            response.raise_for_status()
            created_order = response.json()
        text = (
            f"Order created successfully!\n"
            f"ID: {created_order.get('order_id')}\n"
            f"Type: {created_order.get('order_type')}\n"
            f"Price: {created_order.get('price')}\n"
            f"Volume: {created_order.get('volume')}"
        )
    except Exception as e:
        text = f"Error creating order: {str(e)}"

    await update.message.reply_text(text, reply_markup=get_orders_menu_keyboard())
    return ConversationHandler.END


async def order_cancel(update: Update, _: CallbackContext) -> int:
    """
    Handler for order creation cancellation.
    """
    await update.message.reply_text(
        "Order creation cancelled.", reply_markup=get_orders_menu_keyboard()
    )
    return ConversationHandler.END


# --- Handlers for order details, deletion, and update ---


async def order_detail_handler(update: Update, context: CallbackContext) -> None:
    """
    Handler to display detailed information about an order.
    Expects callback_data in the format "order_detail_<order_id>".
    """
    query = update.callback_query
    await query.answer()
    data = query.data
    order_id = data.split("_", 2)[-1]
    telegram_user_id = str(query.from_user.id)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SERVICE_URL}/api/orders/{telegram_user_id}/{order_id}"
            )
            response.raise_for_status()
            order_data = response.json()

        # Extract the status from the order data
        status = order_data.get("status", "CREATED")

        text = (
            f"<b>Order:</b>\n"
            f"<b>ID:</b> {order_data.get('order_id')}\n"
            f"<b>Type:</b> {order_data.get('order_type')}\n"
            f"<b>Price:</b> {order_data.get('price')}\n"
            f"<b>Volume:</b> {order_data.get('volume')}\n"
            f"<b>Status:</b> {status}\n"
            f"<b>Jetton address:</b> {order_data.get('jetton_address')}\n"
            f"<b>Timestamp:</b> {order_data.get('timestamp')}\n"
        )
        await query.edit_message_text(
            text=text,
            reply_markup=get_order_detail_keyboard(order_id, status),
            parse_mode="HTML",
        )
    except Exception as e:
        await query.edit_message_text(
            text=f"Error retrieving order details: {str(e)}",
            reply_markup=get_orders_menu_keyboard(),
        )


async def order_delete_handler(update: Update, context: CallbackContext) -> None:
    """
    Handler to delete an order.
    Expects the callback_data to be in the format "order_delete_<order_id>".
    """
    query = update.callback_query
    await query.answer()
    data = query.data
    order_id = data.split("_", 2)[-1]
    telegram_user_id = str(query.from_user.id)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{settings.SERVICE_URL}/api/orders/{telegram_user_id}/{order_id}"
            )
            response.raise_for_status()
        await query.edit_message_text(
            text="Order deleted successfully.",
            reply_markup=get_orders_menu_keyboard(),
        )
    except Exception as e:
        await query.edit_message_text(
            text=f"Error deleting order: {str(e)}",
            reply_markup=get_order_detail_keyboard(order_id),
        )


# ---------------- Registration of Handlers ----------------


def register_orders_handlers(app):
    """
    Register handlers for order-related actions:
    - Viewing the list of orders
    - Creating an order (via a ConversationHandler for creation)
    - Viewing order details
    - Deleting an order
    - Updating an order (via a ConversationHandler)
    """
    app.add_handler(CallbackQueryHandler(orders_menu_handler, pattern="^menu_orders"))

    # ConversationHandler for creating an order (assumed to be already registered)
    conv_create_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(order_start, pattern="^order_create$")],
        states={
            0: [CallbackQueryHandler(order_type_callback, pattern="^order_type_")],
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_price_handler)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_volume_handler)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_jetton_handler)],
        },
        fallbacks=[MessageHandler(filters.COMMAND, order_cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv_create_handler)
    app.add_handler(
        CallbackQueryHandler(order_detail_handler, pattern="^order_detail_")
    )
    app.add_handler(
        CallbackQueryHandler(order_delete_handler, pattern="^order_delete_")
    )

    # New ConversationHandler for updating an order.
    # For each step, /skip input is allowed (using Regex to capture both /skip and any other text).
    conv_update_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(update_order_start, pattern="^order_update_")
        ],
        states={
            UPDATE_TYPE: [
                CallbackQueryHandler(
                    update_order_type_callback, pattern="^update_order_type_"
                )
            ],
            UPDATE_PRICE: [
                MessageHandler(filters.Regex(r"^(/skip|.+)$"), update_order_price)
            ],
            UPDATE_VOLUME: [
                MessageHandler(filters.Regex(r"^(/skip|.+)$"), update_order_volume)
            ],
            UPDATE_JETTON: [
                MessageHandler(filters.Regex(r"^(/skip|.+)$"), update_order_jetton)
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, update_order_cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv_update_handler)
