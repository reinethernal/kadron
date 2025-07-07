import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aiogram
from plugin_manager import PluginManager


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
    async def register_handlers(self, dp):
        pass
    def get_commands(self):
        return [BotCommand(command='{cmd}', description='{cmd} desc')]

def load_plugin(bot=None, plugin_manager=None):
    return Plugin()
""".format(cmd=command_name)
    )


def test_setup_bot_commands_collects_from_plugins(tmp_path, monkeypatch):
    pkg_dir = tmp_path / 'testplugins'
    pkg_dir.mkdir()
    (pkg_dir / '__init__.py').write_text('')
    make_plugin_file(pkg_dir / 'one_plugin.py', 'one')
    make_plugin_file(pkg_dir / 'two_plugin.py', 'two')
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.chdir(tmp_path)

    class DummyCommand:
        def __init__(self, command, description):
            self.command = command
            self.description = description
    monkeypatch.setattr(aiogram.types, 'BotCommand', DummyCommand)

    dp = aiogram.Dispatcher()
    bot = DummyBot()
    pm = PluginManager(dp, bot, plugin_dir=pkg_dir)

    asyncio.run(pm.load_plugins())
    asyncio.run(pm.setup_bot_commands(bot))

    assert bot.commands
    assert {c.command for c in bot.commands} == {'one', 'two'}
