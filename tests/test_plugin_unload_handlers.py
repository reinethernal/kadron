import asyncio
import importlib
from pathlib import Path

import aiogram

from plugin_manager import PluginManager
from utils import remove_plugin_handlers


def make_plugin_file(path: Path):
    path.write_text(
        """
from aiogram import Router
from utils import remove_plugin_handlers

class Plugin:
    async def register_handlers(self, router: Router):
        router.message.register(self.echo)

    async def unregister_handlers(self, router: Router):
        remove_plugin_handlers(self, router)

    async def echo(self, message):
        pass

    def get_commands(self):
        return []

def load_plugin(bot=None, plugin_manager=None):
    return Plugin()
"""
    )


def test_unload_removes_handlers(tmp_path, monkeypatch):
    pkg_dir = tmp_path / "plug"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    make_plugin_file(pkg_dir / "simple_plugin.py")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.chdir(tmp_path)

    class DummyHandler:
        def __init__(self):
            self.handlers = []

        def register(self, handler, *args, **kwargs):
            self.handlers.append(handler)

        __call__ = register

    class DummyDispatcher:
        def __init__(self):
            self.message = DummyHandler()
            self.callback_query = DummyHandler()
            self.chat_member = DummyHandler()

        def include_router(self, *args, **kwargs):
            pass

    class DummyRouter(DummyDispatcher):
        pass

    monkeypatch.setattr(aiogram, "Dispatcher", DummyDispatcher, raising=False)
    monkeypatch.setattr(aiogram, "Router", DummyRouter, raising=False)

    pm_module = importlib.reload(importlib.import_module("plugin_manager"))
    dp = pm_module.Dispatcher()
    router = pm_module.Router()
    bot = pm_module.Bot()
    pm = PluginManager(dp, bot, plugin_dir=pkg_dir, router=router)

    asyncio.run(pm.load_plugins())

    assert router.message.handlers
    assert "simple_plugin" in pm.plugins

    asyncio.run(pm.unload_plugin("simple_plugin"))

    assert "simple_plugin" not in pm.plugins
    assert router.message.handlers == []
