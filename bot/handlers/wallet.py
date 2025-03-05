import httpx
from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler

from bot.config import settings
from bot.keyboards import get_main_menu_keyboard, get_wallet_info_keyboard


async def wallet_menu_handler(update: Update, context: CallbackContext) -> None:
    """
    When the "Wallet" button is pressed, display detailed wallet information:
    - Address
    - Balance
    - Total tokens
    - Warning about the private key
    + Buttons
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
            f"<b>Wallet:</b> <code>{address}</code>\n"
            f"(click to copy)\n\n"
            f"Balance: {balance}\n"
            f"Total tokens: {tokens_count}\n\n"
            "If you export your private key, make sure to keep it safe, "
            "otherwise your account may be stolen or compromised\n"
        )

        await query.edit_message_text(
            text=text, reply_markup=get_wallet_info_keyboard(), parse_mode="HTML"
        )
    except Exception as e:
        await query.edit_message_text(
            text=f"Error retrieving wallet data: {str(e)}",
            reply_markup=get_main_menu_keyboard(),
        )


async def wallet_import_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Here you can import your wallet (placeholder).",
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
            f"Address: <code>{export_data.get('address')}</code>\n"
            f"Private key: <code>{export_data.get('mnemonic')}</code>\n"
            "Be careful, do not share your key with anyone!"
        )
        await query.edit_message_text(text=text, parse_mode="HTML")
    except Exception as e:
        await query.edit_message_text(f"Error exporting private key: {str(e)}")


def register_wallet_handlers(app):
    app.add_handler(CallbackQueryHandler(wallet_menu_handler, pattern="^menu_wallet$"))
    app.add_handler(
        CallbackQueryHandler(wallet_import_handler, pattern="^wallet_import$")
    )
    app.add_handler(
        CallbackQueryHandler(wallet_export_handler, pattern="^wallet_export$")
    )
