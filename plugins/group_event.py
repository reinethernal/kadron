import os
import asyncio
import logging
from aiogram import F, Router
from aiogram.types import Message, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from db_manager import (
    get_survey_id_by_name,
    add_user_to_pending,
    is_user_pending,
    remove_user_from_pending,
    get_pending_chats_for_user,
    add_group,
)


class GroupEventPlugin:
    __plugin_meta__ = {
        "name": "group_event",
        "description": "Welcomes new chat members and optionally applies captcha",
        "version": "1.0.0",
    }

    def __init__(self, bot, plugin_manager):
        self.bot = bot
        self.plugin_manager = plugin_manager
        self.router = Router()
        self.enable_captcha = os.getenv("ENABLE_CAPTCHA", "False").lower() == "true"
        self.captcha_timeout = int(os.getenv("CAPTCHA_TIMEOUT", "5"))

    def register_handlers(self):
        self.router.message(F.new_chat_members)(self.welcome_new_member)

    def get_commands(self):
        return []

    async def welcome_new_member(self, message: Message):
        if not message.new_chat_members:
            return

        add_group(message.chat.id, message.chat.title)
        for user in message.new_chat_members:
            chat_id = message.chat.id
            survey_id = get_survey_id_by_name("первичный")
            if not survey_id:
                await self.bot.send_message(chat_id, "Опрос 'первичный' не найден.", parse_mode="HTML")
                return

            bot_username = (await self.bot.get_me()).username
            deep_link = f"https://t.me/{bot_username}?start=survey_{survey_id}_{chat_id}"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Пройти анкетирование", url=deep_link)]]
            )
            await self.bot.send_message(
                chat_id,
                f"Приветствуем, {user.full_name}! Нажмите на кнопку ниже, чтобы пройти анкетирование.",
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            if self.enable_captcha:
                await self.restrict_user(chat_id, user.id)
                add_user_to_pending(user.id, chat_id)
                asyncio.create_task(self.start_captcha_timer(user.id, chat_id))

    async def restrict_user(self, chat_id: int, user_id: int):
        try:
            await self.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
            )
        except TelegramForbiddenError:
            logging.error(f"Bot lacks permission to restrict members in chat {chat_id}")
        except TelegramBadRequest as e:
            logging.error(f"Failed to restrict user {user_id} in chat {chat_id}: {e}")

    async def unrestrict_user_if_needed(self, user_id: int):
        pending_chats = get_pending_chats_for_user(user_id)
        for chat_id in pending_chats:
            try:
                await self.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=True),
                )
                remove_user_from_pending(user_id, chat_id)
            except TelegramForbiddenError:
                logging.error(f"Bot lacks permission to unrestrict members in chat {chat_id}")
            except TelegramBadRequest as e:
                logging.error(f"Failed to unrestrict user {user_id} in chat {chat_id}: {e}")

    async def start_captcha_timer(self, user_id: int, chat_id: int):
        await asyncio.sleep(self.captcha_timeout * 60)
        if is_user_pending(user_id, chat_id):
            try:
                await self.bot.kick_chat_member(chat_id=chat_id, user_id=user_id)
                remove_user_from_pending(user_id, chat_id)
            except TelegramForbiddenError:
                logging.error(f"Bot lacks permission to kick members in chat {chat_id}")
            except TelegramBadRequest as e:
                logging.error(f"Failed to kick user {user_id} from chat {chat_id}: {e}")


def load_plugin(bot, plugin_manager):
    plugin = GroupEventPlugin(bot, plugin_manager)
    plugin.register_handlers()
    return plugin
