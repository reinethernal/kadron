"""
Admin Plugin для Telegram бота.

Здесь реализованы административные функции, например, рассылка опросов.
"""

import logging
from aiogram.client.bot import Bot
from aiogram import Router, types
from aiogram.filters import Command
from core.db_manager import get_all_groups, get_poll_by_id
from dotenv import load_dotenv
from utils.env_utils import parse_admin_ids

load_dotenv()
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
        router.message.register(
            self.cmd_send_survey,
            Command(commands=["send_survey"]),
            lambda msg: msg.from_user.id in ADMIN_IDS,
        )

    def get_commands(self):
        return [
            types.BotCommand(
                command="send_survey",
                description="Разослать опрос по группам",
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

    async def send_survey_to_users(self, poll_id: int, bot: Bot):
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
                await bot.send_message(
                    chat_id=group_id,
                    text=f"Внимание! Новый опрос '{poll_name}': {survey_link}",
                )
                logger.info(f"Опрос '{poll_name}' отправлен в группу {group_id}.")
            except Exception as e:
                logger.error(f"Не удалось отправить опрос в группу {group_id}: {e}")


def load_plugin():
    return AdminPlugin()
