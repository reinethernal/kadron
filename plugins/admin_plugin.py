"""
Admin Plugin для Telegram бота.

Здесь реализованы административные функции, например, рассылка опросов.
"""

import logging
from aiogram.client.bot import Bot
from core.db_manager import get_all_groups, get_poll_by_id
import os
import re
from dotenv import load_dotenv

load_dotenv()
ids = re.findall(r"\d+", os.getenv("ADMIN_IDS", ""))
ADMIN_IDS = [int(x) for x in ids]

logger = logging.getLogger(__name__)

# Оборачиваем административные функции в плагин

class AdminPlugin:
    def __init__(self):
        self.name = "admin_plugin"
        self.description = "Административные функции"
    async def register_handlers(self, dp):
        # Здесь можно зарегистрировать обработчики административных команд.
        pass
    def get_commands(self):
        return []
    def on_plugin_load(self):
        logger.info("Admin plugin loaded")
    def on_plugin_unload(self):
        logger.info("Admin plugin unloaded")
    async def send_survey_to_users(self, poll_id: int, bot: Bot):
        poll = get_poll_by_id(poll_id)
        if not poll:
            logger.error(f"Poll ID {poll_id} not found.")
            return
        poll_name = poll.get("name")
        bot_user = await bot.get_me()
        bot_username = bot_user.username
        survey_link = f"https://t.me/{bot_username}?start=survey_{poll_id}"
        groups = get_all_groups()
        for group in groups:
            group_id = group['group_id']
            try:
                await bot.send_message(
                    chat_id=group_id,
                    text=f"Внимание! Новый опрос '{poll_name}': {survey_link}"
                )
                logger.info(f"Poll '{poll_name}' sent to group {group_id}.")
            except Exception as e:
                logger.error(f"Failed to send poll to group {group_id}: {e}")

def load_plugin():
    return AdminPlugin()
