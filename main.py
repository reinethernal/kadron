# main.py

import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в .env")

from aiogram import Dispatcher
# Здесь пытаемся импортировать DefaultBotProperties, если его нет – игнорируем
try:
    from aiogram.client.bot import Bot, DefaultBotProperties
except ImportError:
    from aiogram.client.bot import Bot
    DefaultBotProperties = None
    logging.warning("DefaultBotProperties not found – bot will be created without parse_mode.")

from core.db_manager import initialize_db
from handlers import admin_handlers, survey_handlers, group_handlers  # group_handlers нужен

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Инициализация БД
    initialize_db()

    # Создание бота
    if DefaultBotProperties:
        bot = Bot(token=BOT_TOKEN, defaults=DefaultBotProperties(parse_mode="HTML"))
    else:
        bot = Bot(token=BOT_TOKEN)

    dp = Dispatcher()

    # Регистрируем хендлеры
    admin_handlers.register_admin_handlers(dp)
    survey_handlers.register_survey_handlers(dp)
    group_handlers.register_group_handlers(dp)  # <-- эта функция должна существовать в group_handlers.py

    logger.info("Бот запущен и ожидает обновлений...")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
