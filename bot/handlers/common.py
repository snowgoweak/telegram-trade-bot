from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from bot.keyboards import get_main_menu_keyboard


async def cmd_start(update: Update, _: CallbackContext) -> None:
    await update.message.reply_text(
        "Welcome! This is your custom trading bot.\n"
        "Blockchain integration will be added later.\n"
        "Please choose an action:",
        reply_markup=get_main_menu_keyboard(),
    )


async def menu_back_handler(update: Update, _: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Main Menu", reply_markup=get_main_menu_keyboard())


def register_common_handlers(dp):
    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CallbackQueryHandler(menu_back_handler, pattern="^menu_back$"))
