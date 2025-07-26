import importlib
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class DummyBot:
    def __init__(self):
        self.sent = []
        self.pinned = []
        self.id = 99
        self.username = "testbot"

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text))

        class Msg:
            def __init__(self, mid):
                self.message_id = mid

        return Msg(len(self.sent))

    async def get_me(self):
        class Me:
            def __init__(self, id_, username):
                self.id = id_
                self.username = username

        return Me(self.id, self.username)

    async def get_chat_member(self, chat_id, user_id):
        class Member:
            status = "administrator"
            can_pin_messages = True

        return Member()

    async def pin_chat_message(self, chat_id, message_id, **kwargs):
        self.pinned.append((chat_id, message_id, kwargs))


def setup_plugin(monkeypatch):
    module = importlib.reload(importlib.import_module("plugins_admin.admin_plugin"))
    monkeypatch.setattr(module, "get_poll_by_id", lambda pid: {"name": "S"})
    monkeypatch.setattr(module, "get_all_groups", lambda: [{"group_id": 1}])
    return module.load_plugin()


def test_send_survey_pins(monkeypatch):
    plugin = setup_plugin(monkeypatch)
    bot = DummyBot()
    asyncio.run(plugin.send_survey_to_users(1, bot))
    assert bot.pinned
    assert bot.pinned[0][2].get("disable_notification") is False


def test_send_survey_skip_pin(monkeypatch):
    plugin = setup_plugin(monkeypatch)
    bot = DummyBot()
    asyncio.run(plugin.send_survey_to_users(1, bot, skip_pin=True))
    assert not bot.pinned
