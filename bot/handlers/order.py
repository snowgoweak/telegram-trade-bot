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

# Состояния диалога для создания ордера
ORDER_TYPE, PRICE, VOLUME, JETTON_ADDRESS = range(4)


def get_order_type_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора типа ордера:
    - Buy (отображается как BUY)
    - Sell (отображается как SELL)
    """
    keyboard = [
        [
            InlineKeyboardButton(text="Buy", callback_data="order_type_buy"),
            InlineKeyboardButton(text="Sell", callback_data="order_type_sell"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# ---------------- Обработчики для Telegram ----------------


async def orders_menu_handler(update: Update, context: CallbackContext) -> None:
    """
    Обработчик для отображения списка ордеров с пагинацией.
    Показывается максимум 5 ордеров за раз.
    Если ордеров больше 5, добавляются кнопки пагинации:
      - «◀ Назад» для перехода на предыдущую страницу (если есть)
      - «Вперед ▶» для перехода на следующую страницу (если есть)
    В нижней части добавлены кнопки "Создать ордер" и "Назад" (в главное меню).
    Callback_data для пагинации: "menu_orders_<page>", где page - номер страницы (начиная с 0).
    Если data равна ровно "menu_orders", считается, что страница 0.
    """
    query = update.callback_query
    await query.answer()

    # Определяем номер страницы из callback_data
    data = query.data
    page = 0
    if data != "menu_orders":
        # Ожидается формат "menu_orders_<page>"
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
            text = "У вас пока нет ордеров."
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="Создать ордер", callback_data="order_create"
                    )
                ],
                [InlineKeyboardButton(text="Назад", callback_data="menu_back")],
            ]
        else:
            text = f"<b>Ваши ордера (страница {page + 1}):</b>\n"
            keyboard = []
            # Для каждого ордера на текущей странице создаем кнопку
            for order in page_orders:
                button_text = (
                    f"Тип: {order.get('order_type')}, " f"Цена: {order.get('price')}"
                )
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            text=button_text,
                            callback_data=f"order_detail_{order.get('order_id')}",
                        )
                    ]
                )

            # Добавляем ряд с кнопками пагинации (если необходимо)
            pagination_buttons = []
            if page > 0:
                pagination_buttons.append(
                    InlineKeyboardButton(
                        text="◀ Назад", callback_data=f"menu_orders_{page - 1}"
                    )
                )
            if end < total_orders:
                pagination_buttons.append(
                    InlineKeyboardButton(
                        text="Вперед ▶", callback_data=f"menu_orders_{page + 1}"
                    )
                )
            if pagination_buttons:
                keyboard.insert(
                    0, pagination_buttons
                )  # вставляем в начало списка кнопок

            # Добавляем ряд с кнопками для создания ордера и возврата в главное меню
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text="Создать ордер", callback_data="order_create"
                    ),
                    InlineKeyboardButton(text="Назад", callback_data="menu_back"),
                ]
            )
        markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=markup, parse_mode="HTML")
    except Exception as e:
        await query.edit_message_text(
            text=f"Ошибка при получении ордеров: {str(e)}",
            reply_markup=get_main_menu_keyboard(),
        )


# --- ConversationHandler для создания ордера ---


async def order_start(update: Update, _: CallbackContext) -> int:
    """
    Точка входа в создание ордера.
    Вызывается при нажатии на кнопку "Создать ордер" (callback_data="order_create").
    Отправляем сообщение с клавиатурой для выбора типа ордера.
    """
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "Выберите тип ордера:", reply_markup=get_order_type_keyboard()
    )
    return ORDER_TYPE


async def order_type_callback(update: Update, context: CallbackContext) -> int:
    """
    Обработка выбора типа ордера через inline-кнопки.
    Если пользователь выбрал «Buy», то order_type = BUY, иначе SELL.
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
            "Некорректный выбор. Повторите, пожалуйста.",
            reply_markup=get_order_type_keyboard(),
        )
        return ORDER_TYPE
    await query.message.edit_text("Введите цену ордера (число):")
    return PRICE


async def order_price_handler(update: Update, context: CallbackContext) -> int:
    try:
        price = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "Цена должна быть числом. Введите цену еще раз:"
        )
        return PRICE
    context.user_data["price"] = price
    await update.message.reply_text("Введите объем ордера (число):")
    return VOLUME


async def order_volume_handler(update: Update, context: CallbackContext) -> int:
    try:
        volume = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "Объем должен быть числом. Введите объем еще раз:"
        )
        return VOLUME
    context.user_data["volume"] = volume
    await update.message.reply_text("Введите адрес jetton:")
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
            f"Ордер создан успешно!\n"
            f"ID: {created_order.get('order_id')}\n"
            f"Тип: {created_order.get('order_type')}\n"
            f"Цена: {created_order.get('price')}\n"
            f"Объем: {created_order.get('volume')}"
        )
    except Exception as e:
        text = f"Ошибка создания ордера: {str(e)}"

    await update.message.reply_text(text, reply_markup=get_orders_menu_keyboard())
    return ConversationHandler.END


async def order_cancel(update: Update, _: CallbackContext) -> int:
    """
    Обработчик отмены создания ордера.
    """
    await update.message.reply_text(
        "Создание ордера отменено.", reply_markup=get_orders_menu_keyboard()
    )
    return ConversationHandler.END


# --- Обработчики для деталей, удаления и обновления ордера ---


async def order_detail_handler(update: Update, _: CallbackContext) -> None:
    """
    Обработчик для отображения деталей ордера.
    В сообщении теперь отображается информация об адресе jettona,
    а также прикрепляется клавиатура для редактирования и удаления.
    Ожидается, что callback_data будет содержать идентификатор ордера в формате "order_detail_<order_id>".
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
        text = (
            f"<b>Ордер:</b>\n"
            f"<b>ID:</b> {order_data.get('order_id')}\n"
            f"<b>Тип:</b> {order_data.get('order_type')}\n"
            f"<b>Цена:</b> {order_data.get('price')}\n"
            f"<b>Объем:</b> {order_data.get('volume')}\n"
            f"<b>Статус:</b> {order_data.get('status')}\n"
            f"<b>Адрес jettona:</b> {order_data.get('jetton_address')}\n"
            f"<b>Время:</b> {order_data.get('timestamp')}\n"
        )
        await query.edit_message_text(
            text=text,
            reply_markup=get_order_detail_keyboard(order_id),
            parse_mode="HTML",
        )
    except Exception as e:
        await query.edit_message_text(
            text=f"Ошибка при получении информации ордера: {str(e)}",
            reply_markup=get_orders_menu_keyboard(),
        )


async def order_delete_handler(update: Update, context: CallbackContext) -> None:
    """
    Обработчик для удаления ордера.
    Ожидается, что callback_data имеет формат "order_delete_<order_id>".
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
            text="Ордер успешно удалён.",
            reply_markup=get_orders_menu_keyboard(),
        )
    except Exception as e:
        await query.edit_message_text(
            text=f"Ошибка при удалении ордера: {str(e)}",
            reply_markup=get_order_detail_keyboard(order_id),
        )


# ---------------- Регистрация обработчиков ----------------


def register_orders_handlers(app):
    """
    Регистрируем обработчики для работы с ордерами:
    - Просмотр списка ордеров
    - Создание ордера (через ConversationHandler для создания)
    - Просмотр деталей ордера
    - Удаление ордера
    - Обновление ордера (через ConversationHandler)
    """
    app.add_handler(CallbackQueryHandler(orders_menu_handler, pattern="^menu_orders"))

    # ConversationHandler для создания ордера (предполагается, что он уже зарегистрирован)
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

    # Новый ConversationHandler для обновления ордера.
    # Для каждого шага разрешаем ввод /skip (используем Regex, чтобы захватывать и /skip, и любой другой текст).
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
