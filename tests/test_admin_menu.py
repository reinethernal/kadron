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


def test_admin_menu_calls(monkeypatch):
    adm_module = importlib.reload(importlib.import_module('plugins.admin_menu_plugin'))
    plugin = adm_module.load_plugin()

    called = {}

    async def fake_create(msg, state):
        called['create'] = msg.text
    monkeypatch.setattr(plugin.survey_plugin, 'cmd_create_survey', fake_create)

    async def fake_export(msg):
        called['export'] = msg.text
    monkeypatch.setattr(plugin.export_plugin, 'cmd_export', fake_export)

    async def fake_test_mode(msg, state):
        called['test_mode'] = msg.text
    monkeypatch.setattr(plugin.test_mode_plugin, 'cmd_test_mode', fake_test_mode)

    state = DummyState()
    msg = DummyMessage('Создать опрос')
    asyncio.run(plugin.handle_surveys_menu(msg, state))
    msg = DummyMessage('Экспорт данных')
    asyncio.run(plugin.handle_analytics_menu(msg, state))
    msg = DummyMessage('Тестовый режим')
    asyncio.run(plugin.handle_settings_menu(msg, state))

    assert called == {'create': 'Создать опрос', 'export': 'Экспорт данных', 'test_mode': 'Тестовый режим'}
