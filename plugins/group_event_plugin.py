"""
Плагин для обработки событий в группе.
"""

import os
import logging
import asyncio
from aiogram.types import ChatPermissions, ChatMemberUpdated, Message
from aiogram.client.bot import Bot
from aiogram import Router
from aiogram.filters import ChatMemberUpdatedFilter
from core.db_manager import (
    is_user_pending,
    remove_user_from_pending,
    get_pending_chats_for_user,
    get_inactive_users,
    get_all_groups,
)
from dotenv import load_dotenv

try:
    from .storage_plugin import storage
except ImportError:

    class DummyStorage:
        def get_setting(self, key, default=None):
            return default

    storage = DummyStorage()

load_dotenv()

ENABLE_CAPTCHA = os.getenv("ENABLE_CAPTCHA", "False").lower() == "true"
CAPTCHA_TIMEOUT = int(os.getenv("CAPTCHA_TIMEOUT", "5"))
INACTIVITY_DAYS = int(os.getenv("INACTIVITY_DAYS", "30"))
ENABLE_INACTIVE_CLEANUP = os.getenv("ENABLE_INACTIVE_CLEANUP", "True").lower() == "true"
DEFAULT_WELCOME_MESSAGE = "Привет, {username}!"

logger = logging.getLogger(__name__)


async def restrict_user(bot: Bot, chat_id: int, user_id: int):
    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False),
        )
        logger.info(f"Пользователь {user_id} ограничен в чате {chat_id}.")
    except Exception as e:
        logger.error(
            f"Не удалось ограничить пользователя {user_id} в чате {chat_id}: {e}"
        )


async def start_captcha_timer(bot: Bot, user_id: int, chat_id: int):
    await asyncio.sleep((CAPTCHA_TIMEOUT - 1) * 60)
    if is_user_pending(user_id, chat_id):
        try:
            await bot.send_message(
                chat_id,
                f"Пользователь {user_id}, у вас осталось 1 минута для прохождения капчи!",
            )
        except Exception as e:
            logger.error(f"Warning message error: {e}")
    await asyncio.sleep(60)
    if is_user_pending(user_id, chat_id):
        try:
            await bot.kick_chat_member(chat_id=chat_id, user_id=user_id)
            logger.info(
                f"Пользователь {user_id} исключён из чата {chat_id} из-за тайм-аута капчи."
            )
            remove_user_from_pending(user_id, chat_id)
        except Exception as e:
            logger.error(
                f"Не удалось исключить пользователя {user_id} из чата {chat_id}: {e}"
            )


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
                    can_add_web_page_previews=True,
                ),
            )
            logger.info(f"Пользователь {user_id} разблокирован в чате {chat_id}.")
            remove_user_from_pending(user_id, chat_id)
        except Exception as e:
            logger.error(
                f"Не удалось снять ограничения с пользователя {user_id} в чате {chat_id}: {e}"
            )


async def remove_inactive_users(bot: Bot):
    while True:
        inactive_users = get_inactive_users(INACTIVITY_DAYS)
        groups = get_all_groups()
        for user in inactive_users:
            for group in groups:
                group_id = group["group_id"]
                try:
                    await bot.kick_chat_member(
                        chat_id=group_id, user_id=user["user_id"]
                    )
                    await bot.unban_chat_member(
                        chat_id=group_id, user_id=user["user_id"]
                    )
                    logger.info(
                        f"Пользователь {user['user_id']} удалён из группы {group_id} за неактивность."
                    )
                except Exception as e:
                    logger.error(
                        f"Не удалось удалить пользователя {user['user_id']} из группы {group_id}: {e}"
                    )
        await asyncio.sleep(86400)


# Оборачиваем функциональность в класс-плагин


class GroupEventPlugin:
    def __init__(self, bot: Bot):
        self.name = "group_event_plugin"
        self.description = "Обработка событий в группе"
        self.bot = bot
        self.cleanup_task = None

    async def register_handlers(self, router: Router):
        """Регистрирует обработчики событий группы."""
        router.chat_member.register(
            self.on_new_chat_member,
            ChatMemberUpdatedFilter(member_status_changed=["member", "creator", "administrator"]),
        )
        router.message.register(
            self.on_private_message, lambda m: getattr(m.chat, "type", "") == "private"
        )

    async def on_new_chat_member(self, event: ChatMemberUpdated):
        user = event.from_user
        if user.is_bot:
            return
        if ENABLE_CAPTCHA:
            await restrict_user(event.bot, event.chat.id, user.id)
            asyncio.create_task(start_captcha_timer(event.bot, user.id, event.chat.id))
        else:
            welcome = storage.get_setting("welcome_message", DEFAULT_WELCOME_MESSAGE)
            try:
                await event.bot.send_message(
                    event.chat.id, welcome.format(username=user.full_name)
                )
            except Exception as e:
                logger.error(f"Не удалось отправить приветственное сообщение: {e}")

    async def on_private_message(self, message: Message):
        await unrestrict_user_if_needed(message.bot, message.from_user.id)

    def get_commands(self):
        return []

    def on_plugin_load(self):
        logger.info("Плагин групповых событий загружен")
        enabled = storage.get_setting(
            "enable_inactive_cleanup", ENABLE_INACTIVE_CLEANUP
        )
        if enabled:
            self.cleanup_task = asyncio.create_task(remove_inactive_users(self.bot))

    def on_plugin_unload(self):
        if self.cleanup_task:
            self.cleanup_task.cancel()
        logger.info("Плагин групповых событий выгружен")


def load_plugin(bot: Bot):
    return GroupEventPlugin(bot)
