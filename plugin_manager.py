"""
Менеджер плагинов Telegram‑бота.

Модуль отвечает за загрузку, выгрузку и управление плагинами бота.
Он предоставляет центральный реестр всех плагинов и их возможностей.
"""

import importlib
import inspect
import os
import logging
from typing import Dict, List, Any, Optional
from aiogram import Dispatcher, Bot
from aiogram.types import BotCommand

logger = logging.getLogger(__name__)


class PluginManager:
    """Управляет всеми плагинами бота"""

    def __init__(self, dp: Dispatcher, bot: Bot):
        self.dp = dp
        self.bot = bot
        self.plugins = {}
        self.plugin_dir = "plugins"

    async def load_plugins(self):
        """Загружает все плагины из каталога plugins"""
        if not os.path.exists(self.plugin_dir):
            logger.warning(f"Каталог плагинов {self.plugin_dir} не найден")
            os.makedirs(self.plugin_dir)
            return

        plugin_files = [
            f
            for f in sorted(os.listdir(self.plugin_dir))
            if f.endswith("_plugin.py") and not f.startswith("__")
        ]

        # Загружаем admin_menu_plugin последним, т.к. он зависит от других
        if "admin_menu_plugin.py" in plugin_files:
            plugin_files.remove("admin_menu_plugin.py")
            plugin_files.append("admin_menu_plugin.py")

        for filename in plugin_files:
            logger.debug(f"Loading plugin file: {filename}")
            plugin_name = filename[:-3]  # убираем расширение .py
            await self.load_plugin(plugin_name)

    async def load_plugin(self, plugin_name: str) -> bool:
        """Загружает конкретный плагин по имени"""
        if plugin_name in self.plugins:
            logger.warning(f"Плагин {plugin_name} уже загружен")
            return False

        try:
            module = importlib.import_module(f"{self.plugin_dir}.{plugin_name}")
            sig = inspect.signature(module.load_plugin)
            kwargs = {}
            if "bot" in sig.parameters:
                kwargs["bot"] = self.bot
            if "plugin_manager" in sig.parameters:
                kwargs["plugin_manager"] = self
            plugin = module.load_plugin(**kwargs)

            # Регистрируем обработчики плагина
            await plugin.register_handlers(self.dp)

            # Вызываем хук загрузки, если он определён
            if hasattr(plugin, "on_plugin_load"):
                plugin.on_plugin_load()

            self.plugins[plugin_name] = plugin
            logger.info(f"Плагин {plugin_name} успешно загружен")
            logger.debug(f"Plugin {plugin_name} imported successfully")
            return True

        except Exception as e:
            logger.exception(f"Не удалось загрузить плагин {plugin_name}: {e}")
            return False

    async def unload_plugin(self, plugin_name: str) -> bool:
        """Выгружает конкретный плагин по имени"""
        if plugin_name not in self.plugins:
            logger.warning(f"Плагин {plugin_name} не загружен")
            return False

        try:
            plugin = self.plugins[plugin_name]

            # Вызываем хук выгрузки, если он определён
            if hasattr(plugin, "on_plugin_unload"):
                plugin.on_plugin_unload()

            # Убираем плагин из реестра
            del self.plugins[plugin_name]

            logger.info(f"Плагин {plugin_name} успешно выгружен")
            return True

        except Exception as e:
            logger.error(f"Не удалось выгрузить плагин {plugin_name}: {e}")
            return False

    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        """Возвращает плагин по имени"""
        return self.plugins.get(plugin_name)

    def get_all_plugins(self) -> Dict[str, Any]:
        """Возвращает все загруженные плагины"""
        return self.plugins

    def get_all_commands(self) -> List[BotCommand]:
        """Получает команды из всех плагинов"""
        commands = []
        for plugin in self.plugins.values():
            if hasattr(plugin, "get_commands"):
                commands.extend(plugin.get_commands())
        return commands

    def get_plugin_commands(self) -> Dict[str, List[BotCommand]]:
        """Возвращает команды, сгруппированные по плагинам"""
        plugin_commands: Dict[str, List[BotCommand]] = {}
        for name, plugin in self.plugins.items():
            if hasattr(plugin, "get_commands"):
                cmds = plugin.get_commands() or []
                plugin_commands[name] = cmds
            else:
                plugin_commands[name] = []
        return plugin_commands

    async def setup_bot_commands(self, bot: Bot):
        """Настраивает команды бота на основе плагинов"""
        commands = self.get_all_commands()
        if commands:
            await bot.set_my_commands(commands)
            logger.info(f"Установлено команд: {len(commands)}")

    def get_all_keyboards(self) -> Dict[str, Any]:
        """Получает все клавиатуры из плагинов"""
        keyboards = {}
        for plugin in self.plugins.values():
            if hasattr(plugin, "get_keyboards"):
                plugin_keyboards = plugin.get_keyboards()
                if plugin_keyboards:
                    keyboards.update(plugin_keyboards)
        return keyboards
