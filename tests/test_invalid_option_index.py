import importlib
import asyncio
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class DummyStorage:
    def __init__(self):
        self.surveys = {}
        self.user_state = {}

    def get_survey(self, sid):
        return self.surveys.get(sid)

    def save_survey(self, sid, data):
        self.surveys[sid] = data

    def get_user_state(self, uid):
        return self.user_state.setdefault(uid, {})

    def set_user_state(self, uid, key, value):
        state = self.user_state.setdefault(uid, {})
        if value is None:
            state.pop(key, None)
        else:
            state[key] = value


class DummyMessage:
    def __init__(self, text, user_id=1):
        self.text = text
        self.from_user = type("U", (), {"id": user_id})
        self.date = datetime.now()
        self.sent = []

    async def answer(self, text, **kw):
        self.sent.append(text)

    async def edit_reply_markup(self, **kw):
        pass


class DummyCallback:
    def __init__(self, data, user_id=1):
        self.data = data
        self.from_user = type("U", (), {"id": user_id})
        self.message = DummyMessage("")
        self.answered = []

    async def answer(self, text=None, **kw):
        self.answered.append(text)


def setup_single(monkeypatch):
    mod = importlib.reload(importlib.import_module("plugins.single_choice_plugin"))
    storage = DummyStorage()
    monkeypatch.setattr(mod, "storage", storage, raising=False)
    monkeypatch.setattr(mod, "add_response", lambda *a: None)
    plugin = mod.load_plugin()
    return plugin, storage


def setup_multi(monkeypatch):
    mod = importlib.reload(importlib.import_module("plugins.multiple_choice_plugin"))
    storage = DummyStorage()
    monkeypatch.setattr(mod, "storage", storage, raising=False)
    monkeypatch.setattr(mod, "add_response", lambda *a: None)
    plugin = mod.load_plugin()
    return plugin, storage


def test_single_invalid_index(monkeypatch):
    plugin, storage = setup_single(monkeypatch)
    survey = {
        "id": "s1",
        "status": "active",
        "is_anonymous": False,
        "questions": [
            {"id": "q1", "text": "Q", "type": "single_choice", "options": ["A"]}
        ],
        "responses": [],
    }
    storage.save_survey("s1", survey)
    cb = DummyCallback("single_choice_s1_q1_5")
    asyncio.run(plugin.process_single_choice_selection(cb))
    assert cb.answered and cb.answered[0] == "Неверный вариант"
    assert not survey["responses"]


def test_multi_invalid_index(monkeypatch):
    plugin, storage = setup_multi(monkeypatch)
    survey = {
        "id": "s1",
        "status": "active",
        "is_anonymous": False,
        "questions": [
            {"id": "q1", "text": "Q", "type": "multiple_choice", "options": ["A"]}
        ],
        "responses": [],
    }
    storage.save_survey("s1", survey)
    cb = DummyCallback("multi_choice_s1_q1_3")
    asyncio.run(plugin.process_multiple_choice_selection(cb))
    assert cb.answered and cb.answered[0] == "Неверный вариант"
    assert not survey["responses"]
