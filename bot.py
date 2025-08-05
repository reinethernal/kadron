import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from admin import register_admin_handlers
from survey import register_survey_handlers
from group_event import register_group_handlers
from db_manager import initialize_db

# Загрузка переменных окружения из .env файла
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_IDS = [int(admin_id) for admin_id in os.getenv('ADMIN_IDS').split(',')]
ENABLE_LOGGING = os.getenv('ENABLE_LOGGING', 'True').lower() == 'true'
LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', 'INFO').upper()

# Настройка логирования
if ENABLE_LOGGING:
    logging.basicConfig(level=getattr(logging, LOGGING_LEVEL, logging.INFO))
    logging.info("Логирование включено")
else:
    logging.disable(logging.CRITICAL)

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
initialize_db()

# Регистрация обработчиков
register_admin_handlers(dp)
register_survey_handlers(dp)
register_group_handlers(dp)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
