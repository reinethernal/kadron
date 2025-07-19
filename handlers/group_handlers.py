# group_handlers.py

import logging
from aiogram import Router, Dispatcher, types
from aiogram.types import Message
from dotenv import load_dotenv
from core.db_manager import add_group, update_user_activity

load_dotenv()
logger = logging.getLogger(__name__)
router = Router()


@router.chat_member()
async def handle_chat_member_update(event: types.ChatMemberUpdated):
    """
    Пример обработки обновления, когда в группу заходит новый участник
    """
    bot = event.bot
    chat = event.chat
    user = event.from_user

    try:
        add_group(chat.id, chat.title)
        update_user_activity(user.id, user.username)

        # Здесь можно добавить логику приветствия, капчи и т.д.
        await bot.send_message(chat.id, f"Привет, {user.full_name}!")
    except Exception as e:
        logger.exception(f"Ошибка обработки участника: {e}")
        await bot.send_message(chat.id, "Произошла ошибка при добавлении участника")


@router.message(lambda msg: msg.chat.type in ["group", "supergroup"])
async def handle_group_message(message: Message):
    """
    Пример простого хендлера, реагирующего на сообщения в группе/супергруппе
    """
    try:
        update_user_activity(message.from_user.id, message.from_user.username)
        add_group(message.chat.id, message.chat.title)
    except Exception as e:
        logger.exception(f"Ошибка обработки сообщения: {e}")
        await message.answer("Произошла ошибка при обработке сообщения")


def register_group_handlers(dp: Dispatcher):
    """
    Функция, которую вызывает main.py для регистрации хендлеров из этого файла.
    """
    dp.include_router(router)

    # Если вы хотите на старте что-то делать (например, удалять неактивных)
    # можно объявить on_startup и зарегистрировать его в диспетчере:
    # async def on_startup(bot: Bot, **kwargs):
    #     ...
    # dp.startup.register(on_startup)
