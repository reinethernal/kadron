"""
Admin menu plugin providing access to other plugin features.

The inline keyboard is built dynamically based on meta-data declared in
loaded plugins. Each plugin can expose menu entries via ``__plugin_meta__``
variable:

__plugin_meta__ = {
    "admin_menu": [
        {"text": "📊 Просмотр опросов", "callback": "view_surveys"},
    ],
    "commands": [
        {"command": "view_surveys", "description": "Просмотр всех опросов"},
    ],
}
"""

import logging

from plugin_manager import PluginManager
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

from utils.env_utils import parse_admin_ids
from utils import remove_plugin_handlers

logger = logging.getLogger(__name__)


__plugin_meta__ = {
    "commands": [
        {"command": "admin", "description": "Админ меню"},
    ]
}


class AdminMenuPlugin:
    """Plugin that shows admin menu generated from plugin meta-data."""

    def __init__(self, plugin_manager: PluginManager):
        self.name = "admin_menu_plugin"
        self.description = "Административное меню"
        self.admin_ids = parse_admin_ids()
        self.plugin_manager = plugin_manager

    async def register_handlers(self, router: Router):
        router.message.register(self.cmd_admin_menu, Command("admin"))
        router.callback_query.register(
            self.admin_menu_callback, lambda c: c.data == "admin_menu"
        )

    async def unregister_handlers(self, router: Router):
        remove_plugin_handlers(self, router)

    def get_commands(self):
        return [types.BotCommand(command="admin", description="Админ меню")]

    async def _show_menu(self, message: types.Message):
        items = self.plugin_manager.get_admin_menu_items()
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=i["text"])] for i in items],
            resize_keyboard=True,
        )
        await message.answer(
            "Добро пожаловать в админ-панель.", reply_markup=keyboard
        )

    async def cmd_admin_menu(self, message: types.Message, state: FSMContext):
        logger.debug(f"{message.text} from {message.from_user.id}")
        if message.from_user.id not in self.admin_ids:
            await message.answer("У вас нет доступа к меню администратора.")
            return
        await self._show_menu(message)
        await state.clear()

    async def admin_menu_callback(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        if callback_query.from_user.id not in self.admin_ids:
            await callback_query.answer("Нет доступа")
            return
        await self._show_menu(callback_query.message)
        await callback_query.answer()
        await state.clear()


def load_plugin(plugin_manager: PluginManager):
    return AdminMenuPlugin(plugin_manager=plugin_manager)
