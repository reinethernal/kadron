"""Plugin that lists loaded plugins."""

from aiogram import Router, types
from aiogram.filters import Command

from plugin_manager import PluginManager
from utils import remove_plugin_handlers

__plugin_meta__ = {
    "admin_menu": [
        {
            "text": "\ud83d\udd0c \u041f\u043b\u0430\u0433\u0438\u043d\u044b",
            "callback": "plugins",
        }
    ],
    "commands": [
        {
            "command": "plugins",
            "description": "\u0421\u043f\u0438\u0441\u043e\u043a \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043d\u043d\u044b\u0445 \u043f\u043b\u0430\u0433\u0438\u043d\u043e\u0432",
        },
    ],
}


class PluginListPlugin:
    """Provides command to list loaded plugins."""

    def __init__(self, plugin_manager: PluginManager):
        self.name = "plugin_list_plugin"
        self.description = "List loaded plugins"
        self.plugin_manager = plugin_manager

    async def register_handlers(self, router: Router):
        router.message.register(self.cmd_plugins, Command("plugins"))
        router.callback_query.register(self.cb_plugins, lambda c: c.data == "plugins")

    async def unregister_handlers(self, router: Router):
        remove_plugin_handlers(self, router)

    async def cmd_plugins(self, message: types.Message):
        names = self.plugin_manager.list_plugin_names()
        text = "\n".join(sorted(names)) if names else "No plugins loaded"
        await message.answer(text)

    async def cb_plugins(self, callback_query: types.CallbackQuery):
        await self.cmd_plugins(callback_query.message)
        await callback_query.answer()


def load_plugin(plugin_manager: PluginManager):
    """Return plugin instance."""
    return PluginListPlugin(plugin_manager)
