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

from aiogram import __version__ as aiogram_version
from packaging.version import parse as parse_version

if parse_version(aiogram_version).major != 3:
    raise RuntimeError(
        "Kadron requires aiogram 3.x. Install dependencies via pip install -r requirements.txt."
    )

if not os.path.exists(".env"):
    logging.warning(
        "Файл .env не найден; переменные окружения не загружены"
    )

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в .env")

ADMIN_IDS = os.getenv("ADMIN_IDS", "")
if not ADMIN_IDS:
    logging.warning(
        "ADMIN_IDS не задан – команда /admin будет недоступна"
    )

# Настройка логирования
ENABLE_LOGGING = os.getenv("ENABLE_LOGGING", "True").lower() == "true"
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO").upper()
level = getattr(logging, LOGGING_LEVEL, logging.INFO) if ENABLE_LOGGING else logging.WARNING
logging.basicConfig(level=level, force=True)
logger = logging.getLogger(__name__)
logger.debug(f"ADMIN_IDS parsed: {ADMIN_IDS}")

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
    plugin_manager = PluginManager(dp, bot)

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
