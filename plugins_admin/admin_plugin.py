"""
Admin Plugin для Telegram бота.

Здесь реализованы административные функции, например, рассылка опросов.
"""

import logging
from aiogram.client.bot import Bot
from aiogram import Router, types
try:
    from aiogram.filters import Command, Text
except Exception:  # pragma: no cover - fallback for test stubs
    from aiogram.filters import Command

    def Text(text):
        return lambda m: getattr(m, "text", None) == text

from core.db_manager import get_all_groups, get_poll_by_id
from utils.env_utils import parse_admin_ids
from utils import remove_plugin_handlers, try_pin_message

__plugin_meta__ = {
    "admin_menu": [
        {"text": "\ud83d\udcec \u0420\u0430\u0441\u0441\u044b\u043b\u043a\u0430", "callback": "send_survey"},
    ],
    "commands": [
        {"command": "send_survey", "description": "\u0420\u0430\u0441\u0441\u044b\u043b\u043a\u0430 \u043e\u043f\u0440\u043e\u0441\u0430"},
    ],
}

ADMIN_IDS = parse_admin_ids()
logger = logging.getLogger(__name__)
logger.debug(f"Parsed ADMIN_IDS: {ADMIN_IDS}")

# Оборачиваем административные функции в плагин


class AdminPlugin:
    def __init__(self):
        self.name = "admin_plugin"
        self.description = "Административные функции"

    async def register_handlers(self, router: Router):
        """Регистрирует обработчики административных команд"""
        router.message.register(self.cmd_send_survey, Command("send_survey"))
        router.message.register(
            self.cmd_send_survey,
            Text("\ud83d\udcec \u0420\u0430\u0441\u0441\u044b\u043b\u043a\u0430"),
        )
        router.callback_query.register(
            self._cb_send_survey,
            lambda c: c.data == "send_survey",
        )

    async def _cb_send_survey(self, callback_query: types.CallbackQuery):
        await self.cmd_send_survey(callback_query.message)

    async def unregister_handlers(self, router: Router):
        remove_plugin_handlers(self, router)

    def get_commands(self):
        """Возвращает список команд плагина"""
        try:
            BotCommandCls = types.BotCommand
        except AttributeError:
            # Fallback for tests where BotCommand may be mocked elsewhere
            from aiogram.types import BotCommand as BotCommandCls

        return [
            BotCommandCls(
                command="send_survey",
                description="Рассылка опроса",
            )
        ]

    async def cmd_send_survey(self, message: types.Message):
        """Команда для рассылки существующего опроса по группам"""
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].isdigit():
            await message.answer("Использование: /send_survey <poll_id>")
            return
        poll_id = int(parts[1])
        await self.send_survey_to_users(poll_id, message.bot)
        await message.answer("Опрос отправлен")

    def on_plugin_load(self):
        logger.info("Плагин администратора загружен")

    def on_plugin_unload(self):
        logger.info("Плагин администратора выгружен")

    async def send_survey_to_users(
        self, poll_id: int, bot: Bot, *, skip_pin: bool = False
    ):
        poll = get_poll_by_id(poll_id)
        if not poll:
            logger.error(f"Опрос с ID {poll_id} не найден.")
            return
        poll_name = poll.get("name")
        bot_user = await bot.get_me()
        bot_username = bot_user.username
        survey_link = f"https://t.me/{bot_username}?start=survey_{poll_id}"
        groups = get_all_groups()
        for group in groups:
            group_id = group["group_id"]
            try:
                msg = await bot.send_message(
                    chat_id=group_id,
                    text=f"Внимание! Новый опрос '{poll_name}': {survey_link}",
                )
                if not skip_pin:
                    await try_pin_message(bot, group_id, msg.message_id)
                logger.info(
                    f"Опрос '{poll_name}' отправлен в группу {group_id}."
                )
            except Exception as e:
                logger.error(f"Не удалось отправить опрос в группу {group_id}: {e}")


def load_plugin():
    return AdminPlugin()
