import os
import logging
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BotCommand, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Bot

from db_manager import (
    add_survey,
    survey_exists,
    add_question,
    get_all_surveys,
    get_survey_id_by_name,
    get_survey_name_by_id,
    get_all_groups,
)


ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class SurveyCreation(StatesGroup):
    waiting_for_survey_name = State()
    waiting_for_questions = State()


class AdminMenuPlugin:
    __plugin_meta__ = {
        "name": "admin_menu",
        "description": "Provides admin panel to manage surveys",
        "version": "1.0.0",
    }

    def __init__(self, bot: Bot, plugin_manager):
        self.bot = bot
        self.plugin_manager = plugin_manager
        self.router = Router()

    def register_handlers(self):
        self.router.message(Command("admin"), F.chat.type == "private")(self.admin_panel)
        self.router.callback_query(F.data == "admin:create")(self.create_survey_start)
        self.router.message(SurveyCreation.waiting_for_survey_name, F.chat.type == "private")(self.receive_survey_name)
        self.router.message(SurveyCreation.waiting_for_questions, F.chat.type == "private")(self.receive_question)
        self.router.message(Command("done"), SurveyCreation.waiting_for_questions, F.chat.type == "private")(self.finish_questions)
        self.router.callback_query(F.data == "admin:resend")(self.show_resend_survey_list)
        self.router.callback_query(F.data.startswith("admin:resend:"))(self.resend_survey)

    def get_commands(self):
        return [BotCommand(command="admin", description="Admin panel")]

    async def admin_panel(self, message: Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            await message.answer("У вас нет прав доступа к административным функциям.", parse_mode="HTML")
            return
        kb = InlineKeyboardBuilder()
        kb.button(text="Создать опрос", callback_data="admin:create")
        kb.button(text="Повторно отправить опрос", callback_data="admin:resend")
        kb.adjust(1)
        await message.answer("Выберите действие:", reply_markup=kb.as_markup(), parse_mode="HTML")
        await state.clear()

    async def create_survey_start(self, call: CallbackQuery, state: FSMContext):
        await call.message.edit_text("Введите название опроса.", parse_mode="HTML")
        await state.set_state(SurveyCreation.waiting_for_survey_name)
        await call.answer()

    async def receive_survey_name(self, message: Message, state: FSMContext):
        name = message.text.strip()
        if survey_exists(name):
            await message.answer(f"Опрос '{name}' уже существует. Введите другое название.", parse_mode="HTML")
            return
        survey_id = add_survey(name)
        await state.update_data(survey_id=survey_id, survey_name=name)
        await message.answer("Введите вопросы по одному. После ввода всех вопросов напишите /done", parse_mode="HTML")
        await state.set_state(SurveyCreation.waiting_for_questions)

    async def receive_question(self, message: Message, state: FSMContext):
        data = await state.get_data()
        survey_id = data.get("survey_id")
        add_question(survey_id, message.text.strip())
        await message.answer("Вопрос добавлен. Введите следующий вопрос или /done для завершения.", parse_mode="HTML")

    async def finish_questions(self, message: Message, state: FSMContext):
        data = await state.get_data()
        survey_name = data.get("survey_name")
        await message.answer(f"Опрос '{survey_name}' успешно создан.", parse_mode="HTML")
        await state.clear()

    async def show_resend_survey_list(self, call: CallbackQuery, state: FSMContext):
        surveys = get_all_surveys()
        if not surveys:
            await call.message.edit_text("Опросы не найдены.", parse_mode="HTML")
            await call.answer()
            return
        kb = InlineKeyboardBuilder()
        for s in surveys:
            survey_id = get_survey_id_by_name(s)
            kb.button(text=s, callback_data=f"admin:resend:{survey_id}")
        kb.adjust(1)
        await call.message.edit_text("Выберите опрос для отправки:", reply_markup=kb.as_markup(), parse_mode="HTML")
        await call.answer()

    async def resend_survey(self, call: CallbackQuery, state: FSMContext, bot: Bot):
        survey_id = int(call.data.split(":")[-1])
        survey_name = get_survey_name_by_id(survey_id)
        groups = get_all_groups()
        if not groups:
            await call.message.edit_text("Бот не состоит ни в одной группе.", parse_mode="HTML")
            await call.answer()
            return
        bot_user = await bot.get_me()
        bot_username = bot_user.username
        for group_id, group_title in groups:
            deep_link = f"https://t.me/{bot_username}?start=survey_{survey_id}_{group_id}"
            text = f"Дорогие друзья, просим вас пройти опрос: [{survey_name}]({deep_link})"
            try:
                sent_message = await bot.send_message(chat_id=group_id, text=text, parse_mode="Markdown")
                if survey_name != "первичный":
                    await bot.pin_chat_message(chat_id=group_id, message_id=sent_message.message_id, disable_notification=False)
            except Exception as e:
                logging.error(f"Ошибка при отправке опроса в группу {group_id}: {e}")
        await call.message.edit_text(f"Опрос '{survey_name}' был успешно отправлен во все группы.", parse_mode="HTML")
        await call.answer()


def load_plugin(bot: Bot, plugin_manager):
    plugin = AdminMenuPlugin(bot, plugin_manager)
    plugin.register_handlers()
    return plugin
