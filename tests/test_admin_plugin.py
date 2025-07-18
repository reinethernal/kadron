import asyncio
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class DummyHandler:
    def __init__(self):
        self.handlers = []

    def register(self, handler, *args, **kwargs):
        self.handlers.append(handler)

    __call__ = register


class DummyRouter:
    def __init__(self):
        self.message = DummyHandler()


def test_admin_plugin_registers_handler(monkeypatch):
    monkeypatch.setenv("ADMIN_IDS", "1")
    for k in list(sys.modules.keys()):
        if k.startswith("plugins."):
            sys.modules.pop(k)

    module = importlib.reload(importlib.import_module("plugins.admin.admin_plugin"))

    class DummyBotCommand:
        def __init__(self, command=None, description=None):
            self.command = command
            self.description = description

    monkeypatch.setattr(module.types, "BotCommand", DummyBotCommand, raising=False)
    plugin = module.load_plugin()
    router = DummyRouter()
    asyncio.run(plugin.register_handlers(router))

    assert plugin.cmd_send_survey in router.message.handlers
    cmds = plugin.get_commands()
    assert not cmds
