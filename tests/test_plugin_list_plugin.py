import asyncio
import importlib


class DummyMessage:
    def __init__(self, text):
        self.text = text
        self.responses = []

    async def answer(self, text, **kwargs):
        self.responses.append(text)


class DummyHandler:
    def __init__(self):
        self.handlers = []

    def register(self, handler, *args, **kwargs):
        self.handlers.append(handler)

    __call__ = register


class DummyRouter:
    def __init__(self):
        self.message = DummyHandler()
        self.callback_query = DummyHandler()


class DummyPM:
    def __init__(self, names=None):
        self.names = names or []

    def list_plugin_names(self):
        return self.names


def test_plugin_list_registers_handlers():
    module = importlib.reload(importlib.import_module("plugins_admin.plugin_list_plugin"))
    pm = DummyPM()
    plugin = module.load_plugin(plugin_manager=pm)
    router = DummyRouter()
    asyncio.run(plugin.register_handlers(router))

    assert plugin.cmd_plugins in router.message.handlers
    assert plugin.cb_plugins in router.callback_query.handlers


def test_cmd_plugins_button_text():
    module = importlib.reload(importlib.import_module("plugins_admin.plugin_list_plugin"))
    pm = DummyPM(["one", "two"])
    plugin = module.load_plugin(plugin_manager=pm)
    msg = DummyMessage("🔌 Плагины")
    asyncio.run(plugin.cmd_plugins(msg))

    assert msg.responses
    assert msg.responses[0] == "one\ntwo"
