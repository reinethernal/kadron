import importlib
import asyncio
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


def test_admin_menu_has_plugin_commands(monkeypatch):
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
        if k.startswith("plugins."):
            sys.modules.pop(k)

    import plugin_manager as pm_module

    pm_module = importlib.reload(pm_module)
    pm = pm_module.PluginManager(
        pm_module.Dispatcher(), pm_module.Bot(), router=pm_module.Router()
    )
    asyncio.run(pm.load_plugins())
    admin = pm.get_plugin("admin_menu_plugin")
    keyboards = admin.get_keyboards()
    plugin_cmds = pm.get_plugin_commands()

    # ensure admin command is exposed
    admin_cmds = plugin_cmds.get("admin_menu_plugin")
    assert any(cmd.command == "admin" for cmd in admin_cmds)
    # exclude admin command from common checks
    plugin_cmds.pop("admin_menu_plugin", None)

    button_texts = []
    for kb in keyboards.values():
        for row in kb.keyboard:
            for btn in row:
                button_texts.append(btn.text)

    for cmds in plugin_cmds.values():
        for cmd in cmds:
            desc = getattr(cmd, "description", None)
            cmd_name = getattr(cmd, "command", None)
            assert any(t == desc or t == cmd_name for t in button_texts)

    survey_texts = []
    for row in keyboards["admin_surveys"].keyboard:
        for btn in row:
            survey_texts.append(btn.text)

    for cmds in plugin_cmds.values():
        for cmd in cmds:
            desc = getattr(cmd, "description", None)
            cmd_name = getattr(cmd, "command", None)
            assert any(t == desc or t == cmd_name for t in survey_texts)
