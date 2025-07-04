import importlib
import asyncio

class DummyUser:
    def __init__(self, id_=1, username="user"):
        self.id = id_
        self.first_name = "F"
        self.last_name = "L"
        self.username = username

class DummyMessage:
    def __init__(self, text):
        self.text = text
        self.from_user = DummyUser()
        self.responses = []

    async def answer(self, text, **kwargs):
        self.responses.append(text)

class DummyState:
    def __init__(self):
        self.data = {}
        self.state = None

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return dict(self.data)

    async def set_state(self, state):
        self.state = state

    async def clear(self):
        self.data.clear()
        self.state = None

class DummyBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text))


def test_start_handler_with_survey(monkeypatch):
    import sys
    import types
    fake_mod = types.ModuleType('plugins.survey_plugin')
    fake_mod.get_questions = lambda pid: ["Q1"]
    monkeypatch.setitem(sys.modules, 'plugins.survey_plugin', fake_mod)
    module = importlib.reload(importlib.import_module("handlers.survey_handlers"))

    monkeypatch.setattr(module, "get_welcome_message", lambda: None)
    monkeypatch.setattr(module, "update_user_activity", lambda u, x=None: None)

    called = {}

    async def fake_send_question(user_id, bot, state):
        data = await state.get_data()
        called["poll"] = (user_id, data.get("poll_id"))

    monkeypatch.setattr(module, "send_question", fake_send_question)

    bot = DummyBot()
    state = DummyState()
    msg = DummyMessage("/start survey_7")

    asyncio.run(module.start_handler(msg, bot, state))

    assert called.get("poll") == (1, 7)
