from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="Wallet", callback_data="menu_wallet")],
        [InlineKeyboardButton(text="Orders", callback_data="menu_orders")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_wallet_info_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard with buttons:
    - Import Wallet
    - Export Private Key
    - Withdraw TON
    - Back
    """
    keyboard = [
        [
            InlineKeyboardButton(text="Import Wallet", callback_data="wallet_import"),
            InlineKeyboardButton(
                text="Export Private Key", callback_data="wallet_export"
            ),
        ],
        [InlineKeyboardButton(text="Withdraw TON", callback_data="wallet_withdraw")],
        [InlineKeyboardButton(text="Back", callback_data="menu_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_orders_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard for the orders menu:
    - Create Order
    - Back (to main menu or previous menu)
    """
    keyboard = [
        [InlineKeyboardButton(text="Create Order", callback_data="order_create")],
        [InlineKeyboardButton(text="Back", callback_data="menu_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_order_detail_keyboard(order_id: str, status: str) -> InlineKeyboardMarkup:
    """
    Keyboard for detailed information about an order:
    - "Edit Order" button (only if status == CREATED)
    - "Delete Order" button
    - "Back" button (to the list of orders)
    """
    # First row of buttons
    buttons = []
    if status == "CREATED":
        buttons.append(
            InlineKeyboardButton(
                text="Edit Order", callback_data=f"order_update_{order_id}"
            )
        )
    buttons.append(
        InlineKeyboardButton(
            text="Delete Order", callback_data=f"order_delete_{order_id}"
        )
    )

    keyboard = [
        buttons,
        [InlineKeyboardButton(text="Back", callback_data="menu_orders")],
    ]
    return InlineKeyboardMarkup(keyboard)
