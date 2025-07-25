import importlib
import asyncio


class DummyUser:
    def __init__(self, id_):
        self.id = id_


class DummyMessage:
    def __init__(self, text, user_id=1):
        self.text = text
        self.from_user = DummyUser(user_id)
        self.responses = []

    async def answer(self, text, **kwargs):
        self.responses.append(text)


class DummyState:
    def __init__(self):
        self.state = None

    async def set_state(self, state):
        self.state = state

    async def clear(self):
        self.state = None


def test_admin_menu_shows_items(monkeypatch):
    monkeypatch.setenv("ADMIN_IDS", "1")
    import aiogram.types as types

    class DummyButton:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

    class DummyMarkup:
        def __init__(self, keyboard=None, **kwargs):
            self.keyboard = keyboard or []

    monkeypatch.setattr(types, "KeyboardButton", DummyButton, raising=False)
    monkeypatch.setattr(types, "ReplyKeyboardMarkup", DummyMarkup, raising=False)
    adm_module = importlib.reload(
        importlib.import_module("plugins_admin.admin_menu_plugin")
    )

    class DummyPM:
        def __init__(self):
            self.called = False

        def get_admin_menu_items(self):
            self.called = True
            return [
                {"text": "Создать опрос", "callback": "create"},
                {"text": "Экспорт данных", "callback": "export"},
            ]

    pm = DummyPM()
    plugin = adm_module.load_plugin(plugin_manager=pm)

    state = DummyState()
    msg = DummyMessage("/admin", user_id=1)
    asyncio.run(plugin.cmd_admin_menu(msg, state))

    assert pm.called
    assert "Добро пожаловать" in msg.responses[0]
