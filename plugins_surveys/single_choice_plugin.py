"""
Плагин для одиночного выбора.
"""

from aiogram import Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from core.db_manager import add_response
from .response_mixin import ResponseMixin
from utils import remove_plugin_handlers
import logging

from plugins_admin.storage_plugin import storage

logger = logging.getLogger(__name__)

__plugin_meta__ = {
    "admin_menu": [],
    "commands": [],
    "permissions": [],
}

OTHER_OPTION = "Другое…"


class SingleChoicePlugin(ResponseMixin):
    def __init__(self):
        self.name = "single_choice_plugin"
        self.description = "Тип вопроса - одиночный выбор"

    async def register_handlers(self, router: Router):
        router.message.register(
            self.process_single_choice_selection,
            lambda m: m.text and m.text.startswith("single_choice_"),
        )
        router.message.register(self.process_other_input)

    async def unregister_handlers(self, router: Router):
        remove_plugin_handlers(self, router)

    def get_commands(self):
        return []

    def get_question_type(self):
        return "single_choice"

    def get_question_type_name(self):
        return "Одиночный выбор"

    def create_question_form(self, question_data=None):
        return {
            "type": "single_choice",
            "name": "Одиночный выбор",
            "fields": [
                {
                    "name": "text",
                    "label": "Текст вопроса",
                    "type": "text",
                    "required": True,
                },
                {
                    "name": "options",
                    "label": "Варианты ответов (по одному в строке)",
                    "type": "textarea",
                    "required": True,
                },
            ],
        }

    def render_question(self, question, survey_id):
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text=f"single_choice_{survey_id}_{question['id']}_{i}"
                    )
                ]
                for i, _ in enumerate(question["options"])
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        return {"text": question["text"], "markup": keyboard}

    async def process_single_choice_selection(
        self, message: types.Message
    ):
        parts = message.text.split("_")
        survey_id = parts[2]
        question_id = parts[3]
        option_index = int(parts[4])
        survey = storage.get_survey(survey_id)
        if not survey or survey["status"] != "active":
            await message.answer("Этот опрос недоступен")
            return
        user_id = message.from_user.id
        question = next(
            (q for q in survey["questions"] if q["id"] == question_id), None
        )
        if question and not (0 <= option_index < len(question["options"])):
            await message.answer("Неверный вариант")
            return
        if question and question["options"][option_index].startswith("Другое"):
            state = storage.get_user_state(user_id)
            state["single_other"] = {"survey_id": survey_id, "question_id": question_id}
            storage.set_user_state(user_id, "single_other", state["single_other"])
            await message.answer("Пожалуйста, введите свой вариант:")
            return

        response = {
            "user_id": None if survey["is_anonymous"] else user_id,
            "question_id": question_id,
            "answer": option_index,
            "timestamp": message.date.isoformat(),
        }
        self._add_or_update_response(survey, user_id, question_id, response)
        add_response(
            survey_id,
            question_id,
            response["user_id"],
            option_index,
            message.date,
        )
        storage.save_survey(survey_id, survey)
        if question:
            await message.answer("Ваш ответ записан!")

    async def process_other_input(self, message: types.Message):
        user_id = message.from_user.id
        state = storage.get_user_state(user_id)
        data = state.get("single_other")
        if not data:
            return
        survey_id = data["survey_id"]
        question_id = data["question_id"]
        survey = storage.get_survey(survey_id)
        if not survey or survey["status"] != "active":
            storage.set_user_state(user_id, "single_other", None)
            return
        response = {
            "user_id": None if survey["is_anonymous"] else user_id,
            "question_id": question_id,
            "answer": message.text,
            "timestamp": message.date.isoformat(),
        }
        self._add_or_update_response(survey, user_id, question_id, response)
        add_response(
            survey_id, question_id, response["user_id"], message.text, message.date
        )
        storage.save_survey(survey_id, survey)
        storage.set_user_state(user_id, "single_other", None)
        await message.answer("✅ Ваш ответ записан!")

    def on_plugin_load(self):
        logger.info("Плагин одиночного выбора загружен")

    def on_plugin_unload(self):
        logger.info("Плагин одиночного выбора выгружен")


def load_plugin():
    return SingleChoicePlugin()
