import importlib
import asyncio
import sys
import os
from pathlib import Path
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
    def __call__(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def register(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


class DummyDispatcher:
    def __init__(self):
        self.message = DummyHandler()
        self.callback_query = DummyHandler()
        self.chat_member = DummyHandler()


class DummyTask:
    def cancel(self):
        pass


async def no_task(*args, **kwargs):
    pass


def test_admin_menu_creates_survey(monkeypatch):
    monkeypatch.setenv("ADMIN_IDS", "1")
    monkeypatch.setenv("ENABLE_INACTIVE_CLEANUP", "False")

    monkeypatch.setattr(aiogram, "Dispatcher", DummyDispatcher, raising=False)
    monkeypatch.setattr(aiogram.types, "BotCommand", DummyBotCommand, raising=False)
    monkeypatch.setattr(aiogram.types, "ReplyKeyboardMarkup", DummyMarkup, raising=False)
    monkeypatch.setattr(aiogram.types, "KeyboardButton", DummyButton, raising=False)
    monkeypatch.setattr(asyncio, "create_task", lambda coro: DummyTask())

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    for k in list(sys.modules.keys()):
        if k.startswith("plugins."):
            sys.modules.pop(k)

    storage_mod = importlib.reload(importlib.import_module("plugins.storage_plugin"))
    storage = DummyStorage()
    monkeypatch.setattr(storage_mod, "storage", storage, raising=False)

    survey_mod = importlib.reload(importlib.import_module("plugins.survey_plugin"))
    monkeypatch.setattr(survey_mod, "storage", storage, raising=False)
    monkeypatch.setattr(survey_mod, "get_all_groups", lambda: [])
    monkeypatch.setattr(
        survey_mod.SurveyPlugin, "_schedule_survey_notifications", lambda self, survey: None
    )

    scheduler_mod = importlib.reload(importlib.import_module("plugins.scheduler_plugin"))
    monkeypatch.setattr(scheduler_mod, "storage", storage, raising=False)
    monkeypatch.setattr(
        scheduler_mod.SchedulerPlugin, "_create_scheduled_task", lambda self, sid, st: None
    )
    monkeypatch.setattr(scheduler_mod, "get_all_groups", lambda: [])

    group_mod = importlib.reload(importlib.import_module("plugins.group_event_plugin"))
    monkeypatch.setattr(group_mod, "storage", storage, raising=False)
    monkeypatch.setattr(group_mod, "remove_inactive_users", lambda bot: None)

    admin_mod = importlib.reload(importlib.import_module("plugins.admin_menu_plugin"))

    pm_module = importlib.reload(importlib.import_module("plugin_manager"))
    dp = pm_module.Dispatcher()
    router = pm_module.Router()
    bot = pm_module.Bot()
    pm = pm_module.PluginManager(dp, bot, router=router)
    asyncio.run(pm.load_plugins())

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
