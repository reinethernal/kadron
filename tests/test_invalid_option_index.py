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


def setup_single(monkeypatch):
    mod = importlib.reload(
        importlib.import_module("plugins_surveys.single_choice_plugin")
    )
    storage = DummyStorage()
    monkeypatch.setattr(mod, "storage", storage, raising=False)
    monkeypatch.setattr(mod, "add_response", lambda *a: None)
    plugin = mod.load_plugin()
    return plugin, storage


def setup_multi(monkeypatch):
    mod = importlib.reload(
        importlib.import_module("plugins_surveys.multiple_choice_plugin")
    )
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
    msg_cmd = DummyMessage("single_choice_s1_q1_5")
    asyncio.run(plugin.process_single_choice_selection(msg_cmd))
    assert msg_cmd.sent and msg_cmd.sent[0] == "Неверный вариант"
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
    msg_cmd = DummyMessage("multi_choice_s1_q1_3")
    asyncio.run(plugin.process_multiple_choice_selection(msg_cmd))
    assert msg_cmd.sent and msg_cmd.sent[0] == "Неверный вариант"
    assert not survey["responses"]
