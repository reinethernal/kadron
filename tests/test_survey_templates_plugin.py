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


def test_survey_templates_plugin_registers_commands(monkeypatch):
    module = importlib.reload(
        importlib.import_module("plugins.surveys.survey_templates_plugin")
    )
    plugin = module.load_plugin()
    router = DummyRouter()
    asyncio.run(plugin.register_handlers(router))

    assert plugin.cmd_save_template in router.message.handlers
    assert plugin.cmd_list_templates in router.message.handlers
    assert plugin.cmd_delete_template in router.message.handlers
    assert plugin.cmd_use_template in router.message.handlers
