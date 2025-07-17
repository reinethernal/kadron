import asyncio
from pathlib import Path
import sys
import os
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aiogram  # noqa: E402
from plugin_manager import PluginManager  # noqa: E402
import plugin_manager  # noqa: E402


class DummyBot(aiogram.Bot):
    def __init__(self):
        super().__init__()
        self.commands = None

    async def set_my_commands(self, commands):
        self.commands = commands


def make_plugin_file(path: Path, command_name: str):
    path.write_text(
        """
from aiogram.types import BotCommand
class Plugin:
    async def register_handlers(self, router):
        pass
    def get_commands(self):
        return [BotCommand(command='{cmd}', description='{cmd} desc')]

def load_plugin(bot=None, plugin_manager=None):
    return Plugin()
""".format(
            cmd=command_name
        )
    )


def test_setup_bot_commands_collects_from_plugins(tmp_path, monkeypatch):
    pkg_dir = tmp_path / "testplugins"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    make_plugin_file(pkg_dir / "one_plugin.py", "one")
    make_plugin_file(pkg_dir / "two_plugin.py", "two")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.chdir(tmp_path)

    class DummyCommand:
        def __init__(self, command, description):
            self.command = command
            self.description = description

    monkeypatch.setattr(aiogram.types, "BotCommand", DummyCommand)
    monkeypatch.setattr(plugin_manager, "BotCommand", DummyCommand)

    dp = aiogram.Dispatcher()
    router = aiogram.Router()
    bot = DummyBot()
    pm = PluginManager(dp, bot, plugin_dir=pkg_dir, router=router)

    asyncio.run(pm.load_plugins())
    asyncio.run(pm.setup_bot_commands(bot))

    assert bot.commands
    assert {c.command for c in bot.commands} == {"start", "one", "two"}


def test_setup_bot_commands_deduplicates(tmp_path, monkeypatch):
    pkg_dir = tmp_path / "dupplugins"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    make_plugin_file(pkg_dir / "a_plugin.py", "dup")
    make_plugin_file(pkg_dir / "b_plugin.py", "dup")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.chdir(tmp_path)

    class DummyCommand:
        def __init__(self, command, description):
            self.command = command
            self.description = description

    monkeypatch.setattr(aiogram.types, "BotCommand", DummyCommand)
    monkeypatch.setattr(plugin_manager, "BotCommand", DummyCommand)

    dp = aiogram.Dispatcher()
    router = aiogram.Router()
    bot = DummyBot()
    pm = PluginManager(dp, bot, plugin_dir=pkg_dir, router=router)

    asyncio.run(pm.load_plugins())
    asyncio.run(pm.setup_bot_commands(bot))

    assert bot.commands
    names = [c.command for c in bot.commands]
    assert names.count("dup") == 1
    assert names.count("start") == 1


def test_plugins_load_from_env_dir(tmp_path, monkeypatch):
    pkg_dir = tmp_path / "external_plugins"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    make_plugin_file(pkg_dir / "ext_plugin.py", "ext")
    monkeypatch.setenv("PLUGIN_DIR", str(pkg_dir))

    dp = aiogram.Dispatcher()
    router = aiogram.Router()
    bot = DummyBot()
    pm = PluginManager(dp, bot, plugin_dir=os.getenv("PLUGIN_DIR"), router=router)

    asyncio.run(pm.load_plugins())

    assert "ext_plugin" in pm.plugins


def test_builtin_plugins_load_from_custom_package(tmp_path, monkeypatch):
    src_dir = Path(__file__).resolve().parents[1] / "plugins"
    pkg_dir = tmp_path / "ext_plugins"
    shutil.copytree(src_dir, pkg_dir)
    monkeypatch.setenv("PLUGIN_DIR", str(pkg_dir))
    monkeypatch.setenv("ENABLE_INACTIVE_CLEANUP", "False")

    class DummyHandler:
        def __call__(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

        register = __call__

    class DummyDispatcher:
        def __init__(self):
            self.message = DummyHandler()
            self.callback_query = DummyHandler()
            self.chat_member = DummyHandler()

    monkeypatch.setattr(aiogram, "Dispatcher", DummyDispatcher, raising=False)

    dp = aiogram.Dispatcher()
    router = aiogram.Router()
    bot = DummyBot()
    pm = PluginManager(dp, bot, plugin_dir=os.getenv("PLUGIN_DIR"), router=router)

    asyncio.run(pm.load_plugins())

    assert "admin_menu_plugin" in pm.plugins


def test_setup_bot_commands_handles_network_error(tmp_path, monkeypatch):
    dp = aiogram.Dispatcher()
    router = aiogram.Router()

    class ErrorBot(DummyBot):
        async def set_my_commands(self, commands):
            raise aiogram.exceptions.TelegramNetworkError("fail")

    bot = ErrorBot()
    pm = PluginManager(dp, bot, plugin_dir=tmp_path, router=router)

    logged = []

    def fake_error(msg, *args, **kwargs):
        logged.append(msg)

    monkeypatch.setattr(plugin_manager.logger, "error", fake_error)

    class DummyCommand:
        def __init__(self, command, description):
            self.command = command
            self.description = description

    monkeypatch.setattr(aiogram.types, "BotCommand", DummyCommand)
    monkeypatch.setattr(plugin_manager, "BotCommand", DummyCommand)

    # Should not raise despite the network error
    asyncio.run(pm.setup_bot_commands(bot))

    assert logged
