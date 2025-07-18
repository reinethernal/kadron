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
    async def set_state(self, state):
        pass


def test_admin_access_denied(monkeypatch):
    monkeypatch.setenv("ADMIN_IDS", "123")
    adm_module = importlib.reload(importlib.import_module("plugins.admin.admin_menu_plugin"))

    class DummyPlugin:
        pass

    class DummyPM:
        def __init__(self):
            self.plugins = {
                "survey_plugin": DummyPlugin(),
                "export_plugin": DummyPlugin(),
                "test_mode_plugin": DummyPlugin(),
                "survey_templates_plugin": DummyPlugin(),
                "roles_plugin": DummyPlugin(),
            }

        def get_plugin(self, name):
            return self.plugins.get(name)

    pm = DummyPM()
    plugin = adm_module.load_plugin(plugin_manager=pm)

    msg = DummyMessage("/admin", user_id=321)
    state = DummyState()
    asyncio.run(plugin.cmd_admin_menu(msg, state))

    assert "У вас нет доступа к меню администратора." in msg.responses
