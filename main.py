# main.py

import asyncio
import logging
import os

from aiogram import __version__ as aiogram_version
from aiogram import Dispatcher
from packaging.version import parse as parse_version
from utils.logging_utils import configure_logging

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
from routers.menu_router import router as menu_router
from handlers.survey_handlers import register_survey_handlers
from handlers.group_handlers import register_group_handlers
from handlers.view_surveys_handler import register_view_surveys_handler

configure_logging()

if parse_version(aiogram_version).major != 3:
    raise RuntimeError(
        "Kadron requires aiogram 3.x. Install dependencies via pip install -r requirements.txt."
    )

if not os.path.exists(".env"):
    logging.warning("Файл .env не найден; переменные окружения не загружены")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в .env")

ADMIN_IDS = os.getenv("ADMIN_IDS", "")
if not ADMIN_IDS:
    logging.warning("ADMIN_IDS не задан – команда /admin будет недоступна")

# Позволяет задать альтернативный каталог с плагинами
PLUGIN_DIR = os.getenv("PLUGIN_DIR")

# Логгер приложения
logger = logging.getLogger(__name__)
logger.debug(f"ADMIN_IDS parsed: {ADMIN_IDS}")


async def main():
    # Инициализация БД
    try:
        initialize_db()
    except Exception as e:
        logger.exception(f"Ошибка инициализации базы данных: {e}")
        return

    # Создание бота
    if DefaultBotProperties:
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    else:
        bot = Bot(token=BOT_TOKEN)

    dp = Dispatcher()

    # Инициализация менеджера плагинов
    plugin_manager = PluginManager(dp, bot, plugin_dir=PLUGIN_DIR, router=menu_router)

    # Загружаем плагины
    try:
        await plugin_manager.load_plugins()
    except Exception as e:
        logger.exception(f"Ошибка загрузки плагинов: {e}")

    # Регистрируем основные хендлеры
    register_survey_handlers(dp)
    register_group_handlers(dp)
    register_view_surveys_handler(dp)

    # Регистрируем команды из плагинов
    await plugin_manager.setup_bot_commands(bot)

    logger.info("Бот запущен и ожидает обновлений...")

    allowed_updates = dp.resolve_used_update_types()

    try:
        await dp.start_polling(bot, allowed_updates=allowed_updates)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
