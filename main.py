# === FILE: main.py ===

import asyncio
import logging
import os

from aiogram import __version__ as aiogram_version
from aiogram import Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import BotCommand
from packaging.version import parse as parse_version
from utils.logging_utils import configure_logging
from utils.env_utils import parse_admin_ids

# Загрузка переменных из .env
from dotenv import load_dotenv

from core.db_manager import initialize_db
from plugin_manager import PluginManager, MissingRequiredPluginsError
from routers.menu_router import router as menu_router
from handlers.survey_handlers import register_survey_handlers
from handlers.group_handlers import register_group_handlers

load_dotenv()

try:
    from aiogram.client.bot import Bot, DefaultBotProperties
except ImportError:  # pragma: no cover - older aiogram
    from aiogram.client.bot import Bot
    DefaultBotProperties = None
    logging.warning(
        "DefaultBotProperties not found – bot will be created with parse_mode parameter"
    )


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

ADMIN_IDS = parse_admin_ids(os.getenv("ADMIN_IDS", ""))

PLUGIN_DIR = os.getenv("PLUGIN_DIR")
ADMIN_PLUGIN_DIR = os.getenv("ADMIN_PLUGIN_DIR")
SURVEY_PLUGIN_DIR = os.getenv("SURVEY_PLUGIN_DIR")

logger = logging.getLogger(__name__)
logger.debug(f"ADMIN_IDS parsed: {ADMIN_IDS}")

router = Router()


@router.message(CommandStart())
async def start_command(message: types.Message):
    await message.answer("Запуск")


@router.message(Command("admin"))
async def admin_command(message: types.Message):
    await message.answer("Админ-панель")


async def main():
    try:
        initialize_db()
    except Exception as e:
        logger.exception(f"Ошибка инициализации базы данных: {e}")
        return

    if DefaultBotProperties:
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    else:
        bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)


    dp = Dispatcher()
    dp.include_router(router)
    dp.include_router(menu_router)

    plugin_manager = PluginManager(
        dp,
        bot,
        plugin_dir=PLUGIN_DIR,
        admin_plugin_dir=ADMIN_PLUGIN_DIR,
        survey_plugin_dir=SURVEY_PLUGIN_DIR,
        router=menu_router,
    )

    try:
        loaded = await plugin_manager.load_plugins(
            required_plugins=["admin_menu_plugin"]
        )
        if not loaded:
            logger.error("Не удалось загрузить ни одного плагина. Завершение работы")
            return
    except MissingRequiredPluginsError as e:
        logger.critical(str(e))
        return
    except Exception as e:
        logger.exception(f"Ошибка загрузки плагинов: {e}")
        return

    register_survey_handlers(dp)
    register_group_handlers(dp)

    await plugin_manager.setup_bot_commands(bot)
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запуск"),
            BotCommand(command="admin", description="Админ-панель"),
        ]
    )

    logger.info("Бот запущен и ожидает обновлений...")
    allowed_updates = dp.resolve_used_update_types()

    try:
        await dp.start_polling(bot, allowed_updates=allowed_updates)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
