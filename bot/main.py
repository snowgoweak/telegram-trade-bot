import logging

from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder

from bot.config import settings
from bot.handlers.common import register_common_handlers
from bot.handlers.order import register_orders_handlers
from bot.handlers.wallet import register_wallet_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()
    app.bot_data["parse_mode"] = ParseMode.HTML

    register_common_handlers(app)
    register_wallet_handlers(app)
    register_orders_handlers(app)

    logger.info("Бот запускается...")
    app.run_polling()


if __name__ == "__main__":
    main()
