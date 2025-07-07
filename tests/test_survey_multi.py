import importlib
from datetime import datetime, timedelta


class DummyStorage:
    def __init__(self):
        self.saved = {}
        self.settings = {}

    def get_survey(self, survey_id):
        return self.saved.get(survey_id)

    def save_survey(self, survey_id, data):
        self.saved[survey_id] = data

    def get_all_surveys(self):
        return self.saved

    def delete_survey(self, survey_id):
        self.saved.pop(survey_id, None)

    def get_user_state(self, user_id):
        return {}

    def set_user_state(self, user_id, key, value):
        pass

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


class DummyState:
    def __init__(self, data):
        self.data = data
        self.state = None

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.data = {}
        self.state = None

    async def set_state(self, state):
        self.state = state


class DummyMessage:
    def __init__(self, text):
        self.text = text
        self.responses = []

    async def answer(self, text, **kwargs):
        self.responses.append(text)


def setup_plugin(monkeypatch):
    module = importlib.reload(importlib.import_module("plugins.survey_plugin"))
    storage = DummyStorage()
    monkeypatch.setattr(module, "storage", storage, raising=False)
    plugin = module.load_plugin()
    return plugin, storage


def test_process_confirmation_multiple(monkeypatch):
    plugin, storage = setup_plugin(monkeypatch)
    questions = [
        {"id": "q1", "text": "Q1", "type": "текстовый ответ", "options": []},
        {"id": "q2", "text": "Q2", "type": "одиночный выбор", "options": ["a", "b"]},
    ]
    data = {
        "title": "Survey",
        "description": "Desc",
        "creator_id": 1,
        "deadline": (datetime.now() + timedelta(hours=1)).isoformat(),
        "is_anonymous": False,
        "questions": questions,
        "scheduled": False,
    }
    state = DummyState(data)
    msg = DummyMessage("Подтвердить")
    import asyncio

    asyncio.run(plugin.process_confirmation(msg, state))
    assert storage.saved
    survey = next(iter(storage.saved.values()))
    assert survey["questions"] == questions


def test_generate_summary_multiple(monkeypatch):
    plugin, _ = setup_plugin(monkeypatch)
    questions = [
        {"id": "q1", "text": "Q1", "type": "текстовый ответ", "options": []},
        {"id": "q2", "text": "Q2", "type": "одиночный выбор", "options": ["a", "b"]},
    ]
    data = {
        "title": "S",
        "description": "D",
        "deadline": datetime.now().isoformat(),
        "is_anonymous": True,
        "questions": questions,
    }
    summary = plugin._generate_survey_summary(data)
    assert "1. Q1" in summary
    assert "2. Q2" in summary
