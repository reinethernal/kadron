from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from db_manager import (
    get_questions_by_survey,
    get_survey_name_by_id,
    get_group_info_by_chat_id,
)
from data_manager import save_to_excel as dm_save_to_excel
from group_event import unrestrict_user_if_needed


class SurveyStates(StatesGroup):
    answering = State()


class SurveyPlugin:
    __plugin_meta__ = {
        "name": "survey",
        "description": "Handles user surveys started via deep links",
        "version": "1.0.0",
    }

    def __init__(self, bot, plugin_manager):
        self.bot = bot
        self.plugin_manager = plugin_manager
        self.router = Router()

    def register_handlers(self):
        self.router.message(CommandStart())(self.start_survey)
        self.router.message(SurveyStates.answering)(self.handle_survey_response)

    def get_commands(self):
        # No additional commands beyond /start
        return []

    async def start_survey(self, message: Message, state: FSMContext):
        args = message.text.split()
        if len(args) <= 1 or not args[1].startswith("survey_"):
            await message.answer("Опрос не найден. Пожалуйста, попробуйте еще раз.", parse_mode="HTML")
            return

        parts = args[1].split("_", 2)
        if len(parts) < 3:
            await message.answer("Некорректный формат ссылки. Пожалуйста, попробуйте еще раз.", parse_mode="HTML")
            return

        try:
            survey_id = int(parts[1])
            chat_id = int(parts[2])
        except ValueError:
            await message.answer("Некорректные идентификаторы опроса или чата.", parse_mode="HTML")
            return

        questions = get_questions_by_survey(survey_id)
        survey_name = get_survey_name_by_id(survey_id)
        if not questions:
            await message.answer("Опрос не найден или не содержит вопросов.", parse_mode="HTML")
            return

        group_info = get_group_info_by_chat_id(chat_id)
        if not group_info:
            await message.answer("Информация о группе не найдена.", parse_mode="HTML")
            return
        group_id, group_name = group_info

        await state.update_data(
            survey_id=survey_id,
            survey_name=survey_name,
            questions=questions,
            current_question=0,
            responses=[],
            group_id=group_id,
            group_name=group_name,
            survey_date=datetime.now().strftime("%d-%m-%Y"),
        )
        await self.ask_next_question(message, state)

    async def ask_next_question(self, message: Message, state: FSMContext):
        data = await state.get_data()
        idx = data["current_question"]
        questions = data["questions"]
        if idx < len(questions):
            await message.answer(questions[idx], parse_mode="HTML")
            await state.set_state(SurveyStates.answering)
        else:
            await self.save_survey_results(message, state)

    async def handle_survey_response(self, message: Message, state: FSMContext):
        data = await state.get_data()
        responses = data.get("responses", [])
        responses.append(message.text)
        await state.update_data(responses=responses, current_question=data["current_question"] + 1)
        await self.ask_next_question(message, state)

    async def save_survey_results(self, message: Message, state: FSMContext):
        data = await state.get_data()
        responses = [
            {"question": q, "answer": a}
            for q, a in zip(data["questions"], data["responses"])
        ]

        user = message.from_user
        dm_save_to_excel(
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name or "",
            username=user.username or "",
            group_id=data.get("group_id"),
            group_name=data.get("group_name"),
            survey_date=data.get("survey_date"),
            responses=responses,
            survey_name=data["survey_name"],
        )
        await message.answer("Спасибо за ваши ответы! Ваши данные сохранены.", parse_mode="HTML")
        await unrestrict_user_if_needed(self.bot, user.id)
        await state.clear()


def load_plugin(bot, plugin_manager):
    plugin = SurveyPlugin(bot, plugin_manager)
    plugin.register_handlers()
    return plugin
