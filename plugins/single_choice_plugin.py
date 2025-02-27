"""
Плагин для одиночного выбора.
"""

from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

try:
    from plugins.storage_plugin import storage
except ImportError:
    class DummyStorage:
        def get_survey(self, survey_id): return {}
        def save_survey(self, survey_id, data): pass
    storage = DummyStorage()

logger = logging.getLogger(__name__)

class SingleChoicePlugin:
    def __init__(self):
        self.name = "single_choice_plugin"
        self.description = "Тип вопроса - одиночный выбор"
    async def register_handlers(self, dp: Dispatcher):
        dp.callback_query.register(self.process_single_choice_selection, lambda c: c.data.startswith('single_choice_'))
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
        markup = InlineKeyboardMarkup(row_width=1)
        for i, option in enumerate(question['options']):
            markup.add(InlineKeyboardButton(
                option,
                callback_data=f"single_choice_{survey_id}_{question['id']}_{i}"
            ))
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
        response = {
            'user_id': None if survey['is_anonymous'] else user_id,
            'question_id': question_id,
            'answer': option_index,
            'timestamp': callback_query.message.date.isoformat()
        }
        self._add_or_update_response(survey, user_id, question_id, response)
        storage.save_survey(survey_id, survey)
        question = next((q for q in survey['questions'] if q['id'] == question_id), None)
        if question:
            options = question['options']
            markup = InlineKeyboardMarkup(row_width=1)
            for i, option in enumerate(options):
                text = f"✅ {option}" if i == option_index else option
                markup.add(InlineKeyboardButton(text, callback_data=f"single_choice_{survey_id}_{question_id}_{i}"))
            await callback_query.message.edit_reply_markup(reply_markup=markup)
        await callback_query.answer("Ваш ответ записан!")
    def _add_or_update_response(self, survey, user_id, question_id, new_response):
        if survey['is_anonymous']:
            survey['responses'].append(new_response)
            return
        for i, response in enumerate(survey['responses']):
            if response.get('user_id') == user_id and response.get('question_id') == question_id:
                survey['responses'][i] = new_response
                return
        survey['responses'].append(new_response)
    def on_plugin_load(self):
        logger.info("Single choice plugin loaded")
    def on_plugin_unload(self):
        logger.info("Single choice plugin unloaded")
def load_plugin():
    return SingleChoicePlugin()
