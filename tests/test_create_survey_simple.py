import importlib, asyncio

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

class DummyUser:
    def __init__(self, id_=1):
        self.id = id_

class DummyMessage:
    def __init__(self, text, user_id=1):
        self.text = text
        self.from_user = DummyUser(user_id)
        self.responses = []
    async def answer(self, text, **kwargs):
        self.responses.append(text)
    async def edit_text(self, text, **kwargs):
        self.responses.append(text)

class DummyCallback:
    def __init__(self, data, user_id=1):
        self.data = data
        self.from_user = DummyUser(user_id)
        self.message = DummyMessage('')
        self.answered = []
    async def answer(self, text=None, **kwargs):
        self.answered.append(text)

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


def setup_plugin(monkeypatch):
    module = importlib.reload(importlib.import_module('plugins.survey_plugin'))
    storage = DummyStorage()
    monkeypatch.setattr(module, 'storage', storage, raising=False)
    monkeypatch.setattr(module, 'get_all_groups', lambda: [])
    monkeypatch.setattr(module.SurveyPlugin, '_schedule_survey_notifications', lambda self, survey: None)
    plugin = module.load_plugin()
    return plugin, storage


def test_create_simple_survey(monkeypatch):
    plugin, storage = setup_plugin(monkeypatch)
    state = DummyState()

    msg = DummyMessage('/create_survey')
    asyncio.run(plugin.cmd_create_survey(msg, state))

    msg = DummyMessage('T')
    asyncio.run(plugin.process_title(msg, state))

    msg = DummyMessage('D')
    asyncio.run(plugin.process_description(msg, state))

    cb = DummyCallback('type_text')
    asyncio.run(plugin.process_question_type_selection(cb, state))

    msg = DummyMessage('Q1')
    asyncio.run(plugin.process_question_text(msg, state))

    msg = DummyMessage('/finish_questions')
    asyncio.run(plugin.cmd_finish_questions(msg, state))

    msg = DummyMessage('1')
    asyncio.run(plugin.process_deadline(msg, state))

    cb = DummyCallback('anon_no')
    asyncio.run(plugin.process_anonymity_selection(cb, state))

    msg = DummyMessage('')
    asyncio.run(plugin.process_target_groups(msg, state))

    cb = DummyCallback('schedule_now')
    asyncio.run(plugin.process_scheduling_selection(cb, state))

    msg = DummyMessage('Подтвердить')
    asyncio.run(plugin.process_confirmation(msg, state))

    assert storage.saved
    survey = next(iter(storage.saved.values()))
    assert survey['title'] == 'T'
    assert survey['description'] == 'D'
    assert survey['creator_id'] == 1
    assert survey['status'] == 'active'
    assert len(survey['questions']) == 1
    q = survey['questions'][0]
    assert q['text'] == 'Q1'
    assert q['type'] == 'текстовый ответ'
