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

    async def answer(self, *a, **kw):
        pass


def setup_single(monkeypatch):
    mod = importlib.reload(
        importlib.import_module("plugins_surveys.single_choice_plugin")
    )
    storage = DummyStorage()
    monkeypatch.setattr(mod, "storage", storage, raising=False)
    called = []
    monkeypatch.setattr(mod, "add_response", lambda *a: called.append(a))
    plugin = mod.load_plugin()
    return plugin, storage, called


def setup_multi(monkeypatch):
    mod = importlib.reload(
        importlib.import_module("plugins_surveys.multiple_choice_plugin")
    )
    storage = DummyStorage()
    monkeypatch.setattr(mod, "storage", storage, raising=False)
    called = []
    monkeypatch.setattr(mod, "add_response", lambda *a: called.append(a))
    plugin = mod.load_plugin()
    return plugin, storage, called


def test_single_other(monkeypatch):
    plugin, storage, called = setup_single(monkeypatch)
    survey = {
        "id": "s1",
        "status": "active",
        "is_anonymous": False,
        "questions": [
            {
                "id": "q1",
                "text": "Q",
                "type": "single_choice",
                "options": ["A", "Другое…"],
            }
        ],
        "responses": [],
    }
    storage.save_survey("s1", survey)
    cb = DummyCallback("single_choice_s1_q1_1")
    asyncio.run(plugin.process_single_choice_selection(cb))
    assert storage.get_user_state(1).get("single_other")
    msg = DummyMessage("X")
    asyncio.run(plugin.process_other_input(msg))
    assert survey["responses"][0]["answer"] == "X"
    assert called


def test_generate_results_other(monkeypatch):
    mod = importlib.reload(importlib.import_module("plugins_surveys.survey_plugin"))
    plugin = mod.load_plugin()
    survey = {
        "title": "T",
        "questions": [
            {
                "id": "q1",
                "text": "Q",
                "type": "одиночный выбор",
                "options": ["A", "Другое…"],
            }
        ],
        "responses": [
            {"question_id": "q1", "answer": 0},
            {"question_id": "q1", "answer": "X"},
        ],
    }
    res = plugin._generate_results(survey)
    assert "Другое" in res
