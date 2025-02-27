"""
Плагин для обработки событий в группе.
"""

import os
import logging
import asyncio
from aiogram.types import ChatPermissions
from aiogram.client.bot import Bot
from core.db_manager import (
    add_group,
    get_welcome_message,
    add_user_to_pending,
    is_user_pending,
    remove_user_from_pending,
    get_pending_chats_for_user,
    update_user_activity,
    get_inactive_users,
    get_all_groups
)
from dotenv import load_dotenv

load_dotenv()

ENABLE_CAPTCHA = os.getenv('ENABLE_CAPTCHA', 'False').lower() == "true"
CAPTCHA_TIMEOUT = int(os.getenv('CAPTCHA_TIMEOUT', '5'))
INACTIVITY_DAYS = int(os.getenv('INACTIVITY_DAYS', '30'))
DEFAULT_WELCOME_MESSAGE = 'Привет, {username}!'

logger = logging.getLogger(__name__)

async def restrict_user(bot: Bot, chat_id: int, user_id: int):
    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        logger.info(f"User {user_id} restricted in chat {chat_id}.")
    except Exception as e:
        logger.error(f"Failed to restrict user {user_id} in chat {chat_id}: {e}")

async def start_captcha_timer(bot: Bot, user_id: int, chat_id: int):
    await asyncio.sleep((CAPTCHA_TIMEOUT - 1) * 60)
    if is_user_pending(user_id, chat_id):
        try:
            await bot.send_message(chat_id, f"Пользователь {user_id}, у вас осталось 1 минута для прохождения капчи!")
        except Exception as e:
            logger.error(f"Warning message error: {e}")
    await asyncio.sleep(60)
    if is_user_pending(user_id, chat_id):
        try:
            await bot.kick_chat_member(chat_id=chat_id, user_id=user_id)
            logger.info(f"User {user_id} kicked from chat {chat_id} due to captcha timeout.")
            remove_user_from_pending(user_id, chat_id)
        except Exception as e:
            logger.error(f"Failed to kick user {user_id} from chat {chat_id}: {e}")

async def unrestrict_user_if_needed(bot: Bot, user_id: int):
    pending_chats = get_pending_chats_for_user(user_id)
    for chat_id in pending_chats:
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
            logger.info(f"User {user_id} unrestricted in chat {chat_id}.")
            remove_user_from_pending(user_id, chat_id)
        except Exception as e:
            logger.error(f"Failed to unrestrict user {user_id} in chat {chat_id}: {e}")

async def remove_inactive_users(bot: Bot):
    while True:
        inactive_users = get_inactive_users()
        groups = get_all_groups()
        for user in inactive_users:
            for group in groups:
                group_id = group['group_id']
                try:
                    await bot.kick_chat_member(chat_id=group_id, user_id=user['user_id'])
                    await bot.unban_chat_member(chat_id=group_id, user_id=user['user_id'])
                    logger.info(f"User {user['user_id']} removed from group {group_id} due to inactivity.")
                except Exception as e:
                    logger.error(f"Failed to remove user {user['user_id']} from group {group_id}: {e}")
        await asyncio.sleep(86400)

# Оборачиваем функциональность в класс-плагин

class GroupEventPlugin:
    def __init__(self):
        self.name = "group_event_plugin"
        self.description = "Обработка событий в группе"
    async def register_handlers(self, dp):
        # При необходимости здесь можно зарегистрировать обработчики событий группы.
        pass
    def get_commands(self):
        return []
    def on_plugin_load(self):
        logger.info("Group Event plugin loaded")
    def on_plugin_unload(self):
        logger.info("Group Event plugin unloaded")

def load_plugin():
    return GroupEventPlugin()
