from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="Wallet", callback_data="menu_wallet")],
        [InlineKeyboardButton(text="Orders", callback_data="menu_orders")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_wallet_info_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопками:
    - Импортировать кошелек
    - Экспортировать приватный ключ
    - Вывести TON
    - Назад
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="Импортировать кошелек", callback_data="wallet_import"
            ),
            InlineKeyboardButton(
                text="Экспортировать приватный ключ", callback_data="wallet_export"
            ),
        ],
        [InlineKeyboardButton(text="Вывести TON", callback_data="wallet_withdraw")],
        [InlineKeyboardButton(text="Назад", callback_data="menu_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_orders_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для меню ордеров:
    - Создать ордер
    - Назад (в главное меню или предыдущее меню)
    """
    keyboard = [
        [InlineKeyboardButton(text="Создать ордер", callback_data="order_create")],
        [InlineKeyboardButton(text="Назад", callback_data="menu_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_order_detail_keyboard(order_id: str) -> InlineKeyboardMarkup:
    """
    Клавиатура для подробной информации об ордере:
    - Кнопка "Редактировать ордер"
    - Кнопка "Удалить ордер"
    - Кнопка "Назад" (в список ордеров)
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="Редактировать ордер", callback_data=f"order_update_{order_id}"
            ),
            InlineKeyboardButton(
                text="Удалить ордер", callback_data=f"order_delete_{order_id}"
            ),
        ],
        [InlineKeyboardButton(text="Назад", callback_data="menu_orders")],
    ]
    return InlineKeyboardMarkup(keyboard)
