# === FILE: plugin_manager.py ===

"""
Менеджер плагинов Telegram‑бота.

Модуль отвечает за загрузку, выгрузку и управление плагинами бота.
Он предоставляет центральный реестр всех плагинов и их возможностей.
"""

import importlib
import inspect
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from aiogram import Dispatcher, Bot, Router
from aiogram.types import BotCommand
from aiogram.exceptions import TelegramNetworkError

logger = logging.getLogger(__name__)


class PluginManager:
    """Управляет всеми плагинами бота"""

    def __init__(
        self,
        dp: Dispatcher,
        bot: Bot,
        plugin_dir: str | None = None,
        router: Router | None = None,
    ):
        self.dp = dp
        self.bot = bot
        self.router = router or Router()
        self.plugins: Dict[str, Any] = {}

        base = Path(__file__).resolve().parent
        if plugin_dir:
            pd = Path(plugin_dir).resolve()
            if (pd / "plugins_admin").is_dir() and (pd / "plugins_surveys").is_dir():
                self.plugin_dirs = [
                    (pd / "plugins_surveys").resolve(),
                    (pd / "plugins_admin").resolve(),
                ]
            else:
                self.plugin_dirs = [pd]
        else:
            self.plugin_dirs = [
                (base / "plugins_surveys").resolve(),
                (base / "plugins_admin").resolve(),
            ]

        for pd in self.plugin_dirs:
            parent = str(pd.parent)
            if parent not in sys.path:
                sys.path.append(parent)

        self._packages = [pd.name for pd in self.plugin_dirs]
        self.plugin_packages: Dict[str, str] = {}

        # compatibility attribute
        self.plugin_dir = self.plugin_dirs[0]

    async def load_plugins(self):
        """Загружает все плагины из каталогов"""
        for pd, pkg in zip(self.plugin_dirs, self._packages):
            if not pd.exists():
                msg = f"Каталог плагинов {pd} не найден"
                logger.error(msg)
                raise FileNotFoundError(msg)

            plugin_files = [
                f.name
                for f in sorted(pd.iterdir())
                if f.is_file()
                and f.name.endswith("_plugin.py")
                and not f.name.startswith("__")
            ]

            if pkg == "plugins_admin" and "admin_menu_plugin.py" in plugin_files:
                plugin_files.remove("admin_menu_plugin.py")
                plugin_files.append("admin_menu_plugin.py")

            for filename in plugin_files:
                logger.debug(f"Loading plugin file: {filename}")
                plugin_name = filename[:-3]
                self.plugin_packages[plugin_name] = pkg
                await self.load_plugin(plugin_name, package=pkg)

        logger.info("Загружены плагины: %s", ", ".join(self.list_plugin_names()))
        include = getattr(self.dp, "include_router", None)
        parent = getattr(self.router, "parent_router", None)
        if callable(include) and parent is None:
            # Ensure the router is attached only once
            include(self.router)

    async def load_plugin(self, plugin_name: str, package: str | None = None) -> bool:
        """Загружает конкретный плагин по имени"""
        if plugin_name in self.plugins:
            logger.warning(f"Плагин {plugin_name} уже загружен")
            return False

        try:
            pkg = package or self.plugin_packages.get(plugin_name)
            if not pkg:
                for pd, pk in zip(self.plugin_dirs, self._packages):
                    if (pd / f"{plugin_name}.py").exists() or (
                        pd / f"{plugin_name}_plugin.py"
                    ).exists():
                        pkg = pk
                        break
            if not pkg:
                pkg = self._packages[0]
            module = importlib.import_module(f"{pkg}.{plugin_name}")
            self.plugin_packages[plugin_name] = pkg
            sig = inspect.signature(module.load_plugin)
            kwargs = {}
            if "bot" in sig.parameters:
                kwargs["bot"] = self.bot
            if "plugin_manager" in sig.parameters:
                kwargs["plugin_manager"] = self
            plugin = module.load_plugin(**kwargs)

            await plugin.register_handlers(self.router)

            if hasattr(plugin, "on_plugin_load"):
                plugin.on_plugin_load()

            self.plugins[plugin_name] = plugin
            logger.info(f"Плагин {plugin_name} успешно загружен")
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
            if hasattr(plugin, "unregister_handlers"):
                await plugin.unregister_handlers(self.router)
            if hasattr(plugin, "on_plugin_unload"):
                plugin.on_plugin_unload()
            del self.plugins[plugin_name]
            logger.info(f"Плагин {plugin_name} успешно выгружен")
            return True
        except Exception as e:
            logger.exception(f"Не удалось выгрузить плагин {plugin_name}: {e}")
            return False

    async def reload_plugin(self, plugin_name: str) -> bool:
        """Перезагружает указанный плагин"""
        pkg = self.plugin_packages.get(plugin_name, self._packages[0])
        module_name = f"{pkg}.{plugin_name}"
        if plugin_name in self.plugins:
            await self.unload_plugin(plugin_name)

        try:
            module = sys.modules.get(module_name)
            if module is not None:
                importlib.reload(module)
            else:
                importlib.import_module(module_name)
        except Exception as e:
            logger.exception(f"Не удалось перезагрузить модуль {plugin_name}: {e}")
            return False

        return await self.load_plugin(plugin_name, package=pkg)

    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        return self.plugins.get(plugin_name)

    def get_all_plugins(self) -> Dict[str, Any]:
        return self.plugins

    def get_all_commands(self) -> List[BotCommand]:
        commands = []
        for plugin in self.plugins.values():
            if hasattr(plugin, "get_commands"):
                try:
                    commands.extend(plugin.get_commands() or [])
                except Exception as e:
                    logger.warning(f"Ошибка get_commands у {plugin.name}: {e}")
        return commands

    def get_plugin_commands(self) -> Dict[str, List[BotCommand]]:
        plugin_commands = {}
        for name, plugin in self.plugins.items():
            if hasattr(plugin, "get_commands"):
                plugin_commands[name] = plugin.get_commands() or []
            else:
                plugin_commands[name] = []
        return plugin_commands

    async def setup_bot_commands(self, bot: Bot):
        commands = [BotCommand(command="start", description="Начать работу с ботом")]
        commands.extend(self.get_all_commands())

        unique: List[BotCommand] = []
        seen: set[str] = set()
        for cmd in commands:
            name = getattr(cmd, "command", None)
            if name and name not in seen:
                unique.append(cmd)
                seen.add(name)

        try:
            await bot.set_my_commands(unique)
        except TelegramNetworkError as e:
            logger.error(f"Failed to set bot commands: {e}")
        except Exception as e:  # pragma: no cover - unexpected errors
            logger.error(f"Failed to set bot commands: {e}")
        else:
            logger.info(f"Установлено {len(unique)} команд")

    def get_all_keyboards(self) -> Dict[str, Any]:
        keyboards = {}
        for plugin in self.plugins.values():
            if hasattr(plugin, "get_keyboards"):
                try:
                    plugin_keyboards = plugin.get_keyboards()
                    if plugin_keyboards:
                        keyboards.update(plugin_keyboards)
                except Exception as e:
                    logger.warning(f"Ошибка get_keyboards у {plugin.name}: {e}")
        return keyboards

    def list_plugin_names(self) -> List[str]:
        return list(self.plugins.keys())
