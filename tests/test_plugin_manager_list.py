import asyncio
from pathlib import Path

import aiogram
from plugin_manager import PluginManager


class DummyBot(aiogram.Bot):
    pass


def make_plugin_file(path: Path, name: str):
    path.write_text(
        """
from aiogram.types import BotCommand
class Plugin:
    async def register_handlers(self, router):
        pass
    def get_commands(self):
        return []

def load_plugin(bot=None, plugin_manager=None):
    return Plugin()
    """
    )


def test_list_plugin_names(tmp_path, monkeypatch):
    pkg_dir = tmp_path / "pluglist"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    make_plugin_file(pkg_dir / "a_plugin.py", "a")
    make_plugin_file(pkg_dir / "b_plugin.py", "b")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.chdir(tmp_path)

    dp = aiogram.Dispatcher()
    router = aiogram.Router()
    bot = DummyBot()
    pm = PluginManager(dp, bot, plugin_dir=pkg_dir, router=router)

    asyncio.run(pm.load_plugins())

    assert set(pm.list_plugin_names()) == {"a_plugin", "b_plugin"}
