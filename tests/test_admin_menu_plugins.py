import asyncio
import importlib
import aiogram.types as types


class DummyBotCommand:
    def __init__(self, command=None, description=None):
        self.command = command
        self.description = description


class DummyButton:
    def __init__(self, text):
        self.text = text


class DummyMarkup:
    def __init__(self, keyboard=None, **kwargs):
        self.keyboard = keyboard or []


def test_admin_menu_collects_menu_items(monkeypatch):
    class DummyHandler:
        def __call__(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

        def register(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

    class DummyDispatcher:
        def __init__(self):
            self.message = DummyHandler()
            self.callback_query = DummyHandler()
            self.chat_member = DummyHandler()

    import aiogram

    monkeypatch.setattr(aiogram, "Dispatcher", DummyDispatcher, raising=False)

    monkeypatch.setattr(types, "BotCommand", DummyBotCommand, raising=False)
    monkeypatch.setattr(types, "ReplyKeyboardMarkup", DummyMarkup, raising=False)
    monkeypatch.setattr(types, "KeyboardButton", DummyButton, raising=False)

    import sys
    import os

    root = os.path.dirname(os.path.dirname(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)

    for k in list(sys.modules.keys()):
        if k.startswith("plugins_admin.") or k.startswith("plugins_surveys."):
            sys.modules.pop(k)

    import plugin_manager as pm_module

    pm_module = importlib.reload(pm_module)
    pm = pm_module.PluginManager(
        pm_module.Dispatcher(), pm_module.Bot(), router=pm_module.Router()
    )
    asyncio.run(pm.load_plugins())
    items = pm.get_admin_menu_items(user_id=1)
    callbacks = {i["callback"] for i in items}

    expected = set()
    for plugin in pm.get_all_plugins().values():
        meta = getattr(plugin, "__plugin_meta__", None)
        if meta and isinstance(meta.get("admin_menu"), list):
            for entry in meta["admin_menu"]:
                expected.add(entry["callback"])

    assert callbacks == expected
