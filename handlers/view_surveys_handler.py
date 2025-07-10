import logging
from aiogram import Router, Dispatcher, types
from aiogram.filters import Command
from core.db_manager import get_all_polls

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("view_surveys"))
async def view_surveys_handler(message: types.Message):
    try:
        polls = get_all_polls()
        if polls:
            await message.answer("Список опросов:\n" + "\n".join(polls))
        else:
            await message.answer("Опросы не найдены.")
    except Exception as e:
        logger.exception(f"Ошибка получения списка опросов: {e}")
        await message.answer("Не удалось получить список опросов. Попробуйте позже.")


def register_view_surveys_handler(dp: Dispatcher):
    dp.include_router(router)
