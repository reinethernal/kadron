# main.py

import asyncio
import logging
import os

from aiogram import Dispatcher
from dotenv import load_dotenv

# Здесь пытаемся импортировать DefaultBotProperties, если его нет – игнорируем
try:
    from aiogram.client.bot import Bot, DefaultBotProperties
except ImportError:
    from aiogram.client.bot import Bot
    DefaultBotProperties = None
    logging.warning(
        "DefaultBotProperties not found – bot will be created without parse_mode."
    )

from core.db_manager import initialize_db
from plugin_manager import PluginManager

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в .env")

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

    # Инициализация менеджера плагинов
    plugin_manager = PluginManager(dp)

    # Загружаем плагины
    await plugin_manager.load_plugins()

    # Регистрируем команды из плагинов
    await plugin_manager.setup_bot_commands(bot)

    logger.info("Бот запущен и ожидает обновлений...")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
