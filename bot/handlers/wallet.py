import httpx
from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler

from bot.config import settings
from bot.keyboards import get_main_menu_keyboard, get_wallet_info_keyboard


async def wallet_menu_handler(update: Update, context: CallbackContext) -> None:
    """
    При нажатии на кнопку «Кошелек» отображаем подробную информацию:
    - Адрес
    - Баланс
    - Общее количество токенов
    - Предупреждение о приватном ключе
    + Кнопки
    """
    query = update.callback_query
    await query.answer()

    telegram_user_id = str(query.from_user.id)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SERVICE_URL}/api/wallet/create/{telegram_user_id}"
            )
            response.raise_for_status()
            wallet_data = response.json()

        address = wallet_data.get("address", "DU8zLf...")
        balance = wallet_data.get("balance", "0 TON")
        tokens_count = wallet_data.get("tokens_count", "0 TON")

        text = (
            f"<b>Кошелек:</b> {address}\n"
            f"(нажмите, чтобы скопировать)\n\n"
            f"Баланс: {balance}\n"
            f"Общее количество токенов: {tokens_count}\n\n"
            "Если вы экспортируете свой приватный ключ, убедитесь в его сохранности, "
            "иначе ваш аккаунт может быть украден либо скомпрометирован\n"
        )

        await query.edit_message_text(
            text=text, reply_markup=get_wallet_info_keyboard(), parse_mode="HTML"
        )
    except Exception as e:
        await query.edit_message_text(
            text=f"Ошибка при получении данных кошелька: {str(e)}",
            reply_markup=get_main_menu_keyboard(),
        )


async def wallet_import_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Здесь можно импортировать кошелек (placeholder).",
        reply_markup=get_wallet_info_keyboard(),
    )


async def wallet_export_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    telegram_user_id = str(query.from_user.id)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SERVICE_URL}/api/wallet/export/{telegram_user_id}",
            )
            response.raise_for_status()
            export_data = response.json()
        text = (
            f"Экспорт:\n"
            f"Адрес: {export_data.get('address')}\n"
            f"Приватный ключ: {export_data.get('mnemonic')}\n"
            "Будьте осторожны, никому не передавайте свой ключ!"
        )
        await query.edit_message_text(text=text)
    except Exception as e:
        await query.edit_message_text(f"Ошибка при экспорте приватного ключа: {str(e)}")


def register_wallet_handlers(app):
    app.add_handler(CallbackQueryHandler(wallet_menu_handler, pattern="^menu_wallet$"))
    app.add_handler(
        CallbackQueryHandler(wallet_import_handler, pattern="^wallet_import$")
    )
    app.add_handler(
        CallbackQueryHandler(wallet_export_handler, pattern="^wallet_export$")
    )
