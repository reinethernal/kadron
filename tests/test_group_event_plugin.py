import asyncio
import importlib


class DummyUser:
    def __init__(self, user_id, is_bot=False, full_name="User"):
        self.id = user_id
        self.is_bot = is_bot
        self.full_name = full_name


class DummyChat:
    def __init__(self, chat_id, title="Group"):
        self.id = chat_id
        self.title = title


class DummyBot:
    async def send_message(self, chat_id, text, **kwargs):
        pass


class DummyEvent:
    def __init__(self, bot, chat_id, user_id, title="Group"):
        self.bot = bot
        self.chat = DummyChat(chat_id, title)
        self.from_user = DummyUser(user_id)


def test_group_added_on_member_update(monkeypatch):
    module = importlib.reload(
        importlib.import_module("plugins_admin.group_event_plugin")
    )
    plugin = module.load_plugin(bot=DummyBot())

    added = {}
    monkeypatch.setattr(
        module,
        "add_group",
        lambda gid, title: added.update({"id": gid, "title": title}),
    )
    monkeypatch.setattr(
        module, "storage", type("S", (), {"get_setting": lambda self, k, d=None: d})()
    )

    event = DummyEvent(plugin.bot, 42, 10, title="G")
    asyncio.run(plugin.on_new_chat_member(event))

    assert added == {"id": 42, "title": "G"}
