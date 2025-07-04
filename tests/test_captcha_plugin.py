import importlib
import asyncio

class DummyUser:
    def __init__(self, id_, is_bot=False):
        self.id = id_
        self.is_bot = is_bot
        self.first_name = "U"

class DummyChat:
    def __init__(self, id_):
        self.id = id_

class DummyBot:
    def __init__(self):
        self.restricted = []
    async def restrict_chat_member(self, chat_id, user_id, permissions):
        self.restricted.append((chat_id, user_id))
    async def send_message(self, chat_id, text, **kwargs):
        pass

class DummyEvent:
    def __init__(self, bot, user_id, chat_id):
        self.bot = bot
        self.from_user = DummyUser(user_id)
        self.chat = DummyChat(chat_id)

class DummyTask:
    def cancel(self):
        pass


def test_join_restrict(monkeypatch):
    module = importlib.reload(importlib.import_module('plugins.captcha_plugin'))
    plugin = module.load_plugin()

    bot = DummyBot()
    event = DummyEvent(bot, 1, 42)

    def fake_create_task(coro):
        coro.close()
        return DummyTask()
    monkeypatch.setattr(asyncio, 'create_task', fake_create_task)
    monkeypatch.setattr(module, 'add_user_to_pending', lambda u, c: None)

    asyncio.run(plugin.on_new_chat_member(event))

    assert bot.restricted == [(42, 1)]
