import importlib
import asyncio
from datetime import datetime, timedelta


class DummyStorage:
    def __init__(self):
        self.settings = {}

    def get_survey(self, survey_id):
        return {
            "deadline": (datetime.now() + timedelta(hours=2)).isoformat(),
            "target_chats": [],
        }

    def save_survey(self, survey_id, data):
        pass

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


class DummyBot:
    def __init__(self):
        self.sent = []
        self.pinned = []
        self.id = 99

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text))

        class DummyMsg:
            def __init__(self, message_id):
                self.message_id = message_id

        return DummyMsg(len(self.sent))

    async def get_me(self):
        class Me:
            def __init__(self, id_):
                self.id = id_

        return Me(self.id)

    async def get_chat_member(self, chat_id, user_id):
        class Member:
            status = "administrator"
            can_pin_messages = True

        return Member()

    async def pin_chat_message(self, chat_id, message_id, **kwargs):
        self.pinned.append((chat_id, message_id))


def test_restore_scheduled(monkeypatch):
    storage = DummyStorage()
    future = datetime.now() + timedelta(hours=1)
    storage.set_setting(
        "scheduled_surveys",
        [
            {
                "survey_id": "s1",
                "scheduled_time": future.isoformat(),
                "created_by": 1,
                "created_at": datetime.now().isoformat(),
            }
        ],
    )

    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    tasks = []

    def fake_create_task(func, *args, **kwargs):
        tasks.append((func, args, kwargs))

        class Dummy:
            pass

        return Dummy()

    module = importlib.reload(importlib.import_module("plugins_surveys.scheduler_plugin"))
    monkeypatch.setattr(module, "storage", storage, raising=False)
    bot = DummyBot()
    plugin = module.load_plugin(bot)
    monkeypatch.setattr(plugin, "_create_task", fake_create_task)
    plugin.on_plugin_load()

    assert "s1" in plugin.scheduled_tasks


def test_scheduled_send(monkeypatch):
    storage = DummyStorage()
    storage.surveys = {
        "s1": {
            "title": "T",
            "description": "D",
            "deadline": (datetime.now() + timedelta(hours=1)).isoformat(),
            "target_chats": [42],
            "status": "pending",
        }
    }
    storage.settings["scheduled_surveys"] = [{"survey_id": "s1"}]
    monkeypatch.setattr(storage, "get_survey", lambda sid: storage.surveys.get(sid))

    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    module = importlib.reload(importlib.import_module("plugins_surveys.scheduler_plugin"))
    monkeypatch.setattr(module, "storage", storage, raising=False)

    bot = DummyBot()
    plugin = module.load_plugin(bot)

    async def fake_sleep(delay):
        pass

    monkeypatch.setattr(module.asyncio, "sleep", fake_sleep)

    def fake_task(func, *args, **kwargs):
        class Dummy:
            def cancel(self):
                pass

        return Dummy()

    monkeypatch.setattr(plugin, "_create_task", fake_task)

    asyncio.run(plugin._send_scheduled_survey("s1", 0))

    assert bot.sent
    assert bot.pinned
