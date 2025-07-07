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

    add_group(chat.id, chat.title)
    update_user_activity(user.id, user.username)

    # Здесь можно добавить логику приветствия, капчи и т.д.
    await bot.send_message(chat.id, f"Привет, {user.full_name}!")


@router.message(lambda msg: msg.chat.type in ["group", "supergroup"])
async def handle_group_message(message: Message):
    """
    Пример простого хендлера, реагирующего на сообщения в группе/супергруппе
    """
    update_user_activity(message.from_user.id, message.from_user.username)
    add_group(message.chat.id, message.chat.title)


def register_group_handlers(dp: Dispatcher):
    """
    Функция, которую вызывает main.py для регистрации хендлеров из этого файла.
    """
    dp.include_router(router)

    # Если вы хотите на старте что-то делать (например, удалять неактивных)
    # можно объявить on_startup:
    # from plugins.group_event_plugin import remove_inactive_users
    #
    # async def on_startup(bot: Bot, **kwargs):
    #     asyncio.create_task(remove_inactive_users(bot))
    #
    # dp.startup.register(on_startup)
