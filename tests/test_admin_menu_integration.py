import importlib
import asyncio
import sys
import aiogram


class DummyBotCommand:
    def __init__(self, command=None, description=None):
        self.command = command
        self.description = description


class DummyButton:
    def __init__(self, text):
        self.text = text


class DummyMarkup:
    def __init__(self, keyboard=None, **kwargs):
        self.keyboard = keyboard or []


class DummyStorage:
    def __init__(self):
        self.saved = {}
        self.settings = {}
        self.storage_file = "dummy.json"

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
        self.message = DummyMessage("")
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


class DummyHandler:
    def __init__(self):
        self.handlers = []

    def __call__(self, *args, **kwargs):
        def decorator(func):
            self.handlers.append(func)
            return func

        return decorator

    def register(self, handler, *args, **kwargs):
        self.handlers.append(handler)


class DummyDispatcher:
    def __init__(self):
        self.message = DummyHandler()
        self.callback_query = DummyHandler()
        self.chat_member = DummyHandler()


class DummyRouter:
    def __init__(self):
        self.message = DummyHandler()
        self.callback_query = DummyHandler()
        self.chat_member = DummyHandler()

    def include_router(self, *args, **kwargs):
        pass


class DummyTask:
    def cancel(self):
        pass


async def no_task(*args, **kwargs):
    pass


def test_admin_menu_creates_survey(monkeypatch):
    monkeypatch.setenv("ADMIN_IDS", "1")
    monkeypatch.setenv("ENABLE_CAPTCHA", "True")
    monkeypatch.setenv("ENABLE_INACTIVE_CLEANUP", "False")

    monkeypatch.setattr(aiogram, "Dispatcher", DummyDispatcher, raising=False)
    monkeypatch.setattr(aiogram, "Router", DummyRouter, raising=False)
    monkeypatch.setattr(aiogram.types, "BotCommand", DummyBotCommand, raising=False)
    monkeypatch.setattr(
        aiogram.types, "ReplyKeyboardMarkup", DummyMarkup, raising=False
    )
    monkeypatch.setattr(aiogram.types, "KeyboardButton", DummyButton, raising=False)
    monkeypatch.setattr(asyncio, "create_task", lambda coro: DummyTask())

    for k in list(sys.modules.keys()):
        if k.startswith("plugins."):
            sys.modules.pop(k)

    storage_mod = importlib.reload(importlib.import_module("plugins.surveys.storage_plugin"))
    storage = DummyStorage()
    monkeypatch.setattr(storage_mod, "storage", storage, raising=False)

    survey_mod = importlib.reload(importlib.import_module("plugins.surveys.survey_plugin"))
    monkeypatch.setattr(survey_mod, "storage", storage, raising=False)
    monkeypatch.setattr(survey_mod, "get_all_groups", lambda: [])
    monkeypatch.setattr(
        survey_mod.SurveyPlugin,
        "_schedule_survey_notifications",
        lambda self, survey: None,
    )

    scheduler_mod = importlib.reload(
        importlib.import_module("plugins.surveys.scheduler_plugin")
    )
    monkeypatch.setattr(scheduler_mod, "storage", storage, raising=False)
    monkeypatch.setattr(
        scheduler_mod.SchedulerPlugin,
        "_create_scheduled_task",
        lambda self, sid, st: None,
    )
    monkeypatch.setattr(scheduler_mod, "get_all_groups", lambda: [])

    group_mod = importlib.reload(importlib.import_module("plugins.admin.group_event_plugin"))
    monkeypatch.setattr(group_mod, "storage", storage, raising=False)
    monkeypatch.setattr(group_mod, "remove_inactive_users", lambda bot: None)
    called = {}

    async def fake_restrict(bot, chat_id, user_id):
        called["restrict"] = (chat_id, user_id)

    def fake_timer(bot, user_id, chat_id):
        called["timer"] = (user_id, chat_id)

    async def fake_unrestrict(bot, user_id):
        called["unrestrict"] = user_id

    monkeypatch.setattr(group_mod, "restrict_user", fake_restrict, raising=False)
    monkeypatch.setattr(group_mod, "start_captcha_timer", fake_timer, raising=False)
    monkeypatch.setattr(
        group_mod, "unrestrict_user_if_needed", fake_unrestrict, raising=False
    )

    importlib.reload(importlib.import_module("plugins.admin.admin_menu_plugin"))

    pm_module = importlib.reload(importlib.import_module("plugin_manager"))
    dp = pm_module.Dispatcher()
    router = pm_module.Router()
    bot = pm_module.Bot()
    pm = pm_module.PluginManager(dp, bot, router=router)
    asyncio.run(pm.load_plugins())

    group = pm.get_plugin("group_event_plugin")
    assert group.on_new_chat_member in router.chat_member.handlers
    assert group.on_private_message in router.message.handlers

    event = type(
        "Ev",
        (),
        {
            "bot": bot,
            "chat": type("C", (), {"id": 42})(),
            "from_user": type("U", (), {"id": 1, "full_name": "U", "is_bot": False})(),
        },
    )()
    asyncio.run(group.on_new_chat_member(event))
    msg = type(
        "Msg",
        (),
        {
            "bot": bot,
            "chat": type("Chat", (), {"type": "private", "id": 1})(),
            "from_user": DummyUser(),
        },
    )()
    asyncio.run(group.on_private_message(msg))

    assert called["restrict"] == (42, 1)
    assert called["timer"] == (1, 42)
    assert called["unrestrict"] == 1

    admin = pm.get_plugin("admin_menu_plugin")
    survey = pm.get_plugin("survey_plugin")

    assert admin.plugin_manager is pm
    assert admin.survey_plugin is survey

    state = DummyState()
    msg = DummyMessage("/admin")
    asyncio.run(admin.cmd_admin_menu(msg, state))

    msg = DummyMessage("📊 Опросы")
    asyncio.run(admin.handle_main_menu(msg, state))

    msg = DummyMessage("Создать опрос")
    asyncio.run(admin.handle_surveys_menu(msg, state))

    msg = DummyMessage("T")
    asyncio.run(survey.process_title(msg, state))
    msg = DummyMessage("D")
    asyncio.run(survey.process_description(msg, state))
    cb = DummyCallback("type_text")
    asyncio.run(survey.process_question_type_selection(cb, state))
    msg = DummyMessage("Q1")
    asyncio.run(survey.process_question_text(msg, state))
    msg = DummyMessage("/finish_questions")
    asyncio.run(survey.cmd_finish_questions(msg, state))
    msg = DummyMessage("1")
    asyncio.run(survey.process_deadline(msg, state))
    cb = DummyCallback("anon_no")
    asyncio.run(survey.process_anonymity_selection(cb, state))
    msg = DummyMessage("")
    asyncio.run(survey.process_target_groups(msg, state))
    cb = DummyCallback("schedule_now")
    asyncio.run(survey.process_scheduling_selection(cb, state))
    msg = DummyMessage("Подтвердить")
    asyncio.run(survey.process_confirmation(msg, state))

    assert storage.saved
    created = next(iter(storage.saved.values()))
    assert created["title"] == "T"
    assert created["description"] == "D"
    assert created["creator_id"] == 1
    assert created["status"] == "active"
    assert created["questions"][0]["text"] == "Q1"
    assert created["questions"][0]["type"] == "текстовый ответ"
