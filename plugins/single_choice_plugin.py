"""
Плагин для одиночного выбора.
"""

from aiogram import Dispatcher, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.db_manager import add_response
from plugins.response_mixin import ResponseMixin
import logging

try:
    from plugins.storage_plugin import storage
except ImportError:
    class DummyStorage:
        def get_survey(self, survey_id): return {}
        def save_survey(self, survey_id, data): pass
    storage = DummyStorage()

logger = logging.getLogger(__name__)

OTHER_OPTION = "Другое…"

class SingleChoicePlugin(ResponseMixin):
    def __init__(self):
        self.name = "single_choice_plugin"
        self.description = "Тип вопроса - одиночный выбор"
    async def register_handlers(self, dp: Dispatcher):
        dp.callback_query.register(
            self.process_single_choice_selection,
            lambda c: c.data.startswith('single_choice_')
        )
        dp.message.register(self.process_other_input)
    def get_commands(self):
        return []
    def get_question_type(self):
        return "single_choice"
    def get_question_type_name(self):
        return "Одиночный выбор"
    def create_question_form(self, question_data=None):
        return {
            'type': 'single_choice',
            'name': 'Одиночный выбор',
            'fields': [
                {'name': 'text', 'label': 'Текст вопроса', 'type': 'text', 'required': True},
                {'name': 'options', 'label': 'Варианты ответов (по одному в строке)', 'type': 'textarea', 'required': True}
            ]
        }
    def render_question(self, question, survey_id):
        builder = InlineKeyboardBuilder()
        for i, option in enumerate(question['options']):
            builder.button(
                text=option,
                callback_data=f"single_choice_{survey_id}_{question['id']}_{i}"
            )
        builder.adjust(1)
        markup = builder.as_markup()
        return {'text': question['text'], 'markup': markup}
    async def process_single_choice_selection(self, callback_query: types.CallbackQuery):
        parts = callback_query.data.split('_')
        survey_id = parts[2]
        question_id = parts[3]
        option_index = int(parts[4])
        survey = storage.get_survey(survey_id)
        if not survey or survey['status'] != 'active':
            await callback_query.answer("Этот опрос недоступен")
            return
        user_id = callback_query.from_user.id
        question = next((q for q in survey['questions'] if q['id'] == question_id), None)
        if question and not (0 <= option_index < len(question['options'])):
            await callback_query.answer("Неверный вариант")
            return
        if question and question['options'][option_index].startswith('Другое'):
            state = storage.get_user_state(user_id)
            state['single_other'] = {'survey_id': survey_id, 'question_id': question_id}
            storage.set_user_state(user_id, 'single_other', state['single_other'])
            await callback_query.message.answer('Пожалуйста, введите свой вариант:')
            await callback_query.answer()
            return

        response = {
            'user_id': None if survey['is_anonymous'] else user_id,
            'question_id': question_id,
            'answer': option_index,
            'timestamp': callback_query.message.date.isoformat()
        }
        self._add_or_update_response(survey, user_id, question_id, response)
        add_response(survey_id, question_id, response['user_id'], option_index, callback_query.message.date)
        storage.save_survey(survey_id, survey)
        if question:
            options = question['options']
            builder = InlineKeyboardBuilder()
            for i, option in enumerate(options):
                text = f"✅ {option}" if i == option_index else option
                builder.button(
                    text=text,
                    callback_data=f"single_choice_{survey_id}_{question_id}_{i}"
                )
            builder.adjust(1)
            markup = builder.as_markup()
            await callback_query.message.edit_reply_markup(reply_markup=markup)
        await callback_query.answer("Ваш ответ записан!")

    async def process_other_input(self, message: types.Message):
        user_id = message.from_user.id
        state = storage.get_user_state(user_id)
        data = state.get('single_other')
        if not data:
            return
        survey_id = data['survey_id']
        question_id = data['question_id']
        survey = storage.get_survey(survey_id)
        if not survey or survey['status'] != 'active':
            storage.set_user_state(user_id, 'single_other', None)
            return
        response = {
            'user_id': None if survey['is_anonymous'] else user_id,
            'question_id': question_id,
            'answer': message.text,
            'timestamp': message.date.isoformat()
        }
        self._add_or_update_response(survey, user_id, question_id, response)
        add_response(survey_id, question_id, response['user_id'], message.text, message.date)
        storage.save_survey(survey_id, survey)
        storage.set_user_state(user_id, 'single_other', None)
        await message.answer("✅ Ваш ответ записан!")
    def on_plugin_load(self):
        logger.info("Плагин одиночного выбора загружен")
    def on_plugin_unload(self):
        logger.info("Плагин одиночного выбора выгружен")
def load_plugin():
    return SingleChoicePlugin()
