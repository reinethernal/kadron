"""
Multiple Choice Plugin for Telegram Bot (aiogram 3.x)

This plugin provides multiple choice question type functionality.
It handles rendering and processing multiple choice questions.
"""

import logging
import asyncio

from aiogram import Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Поправленные импорты для хранилища
try:
    from plugins.storage_plugin import storage
except ImportError:
    # Fallback for testing
    class DummyStorage:
        def get_survey(self, survey_id): return {}
        def save_survey(self, survey_id, data): pass
        def get_user_state(self, user_id): return {}
        def set_user_state(self, user_id, key, value): pass
    storage = DummyStorage()

logger = logging.getLogger(__name__)

class MultipleChoicePlugin:
    """Plugin for multiple choice question type"""

    def __init__(self):
        self.name = "multiple_choice_plugin"
        self.description = "Multiple choice question type"

    async def register_handlers(self, dp: Dispatcher):
        """Register all handlers for this plugin (aiogram 3.x style)"""
        dp.callback_query.register(
            self.process_multiple_choice_selection,
            lambda c: c.data.startswith('multi_choice_')
        )
        dp.callback_query.register(
            self.process_multiple_choice_submit,
            lambda c: c.data.startswith('multi_submit_')
        )

    def get_commands(self):
        """Return a list of commands this plugin provides"""
        return []

    def get_question_type(self):
        """Return the question type identifier"""
        return "multiple_choice"

    def get_question_type_name(self):
        """Return the human-readable question type name"""
        return "Множественный выбор"

    def create_question_form(self, question_data=None):
        """Return form for creating this question type"""
        return {
            'type': 'multiple_choice',
            'name': 'Множественный выбор',
            'fields': [
                {'name': 'text', 'label': 'Текст вопроса', 'type': 'text', 'required': True},
                {'name': 'options', 'label': 'Варианты ответов (по одному в строке)', 'type': 'textarea', 'required': True}
            ]
        }

    def render_question(self, question, survey_id):
        """Render the question for users to answer"""
        markup = InlineKeyboardMarkup(row_width=1)

        for i, option in enumerate(question['options']):
            markup.add(InlineKeyboardButton(
                option,
                callback_data=f"multi_choice_{survey_id}_{question['id']}_{i}"
            ))

        markup.add(InlineKeyboardButton(
            "Подтвердить выбор",
            callback_data=f"multi_submit_{survey_id}_{question['id']}"
        ))

        return {
            'text': question['text'] + "\n\nВыберите один или несколько вариантов:",
            'markup': markup
        }

    async def process_multiple_choice_selection(self, callback_query: CallbackQuery):
        """Process user's selection for multiple choice question"""
        parts = callback_query.data.split('_')
        # Примерный формат: multi_choice_<survey_id>_<question_id>_<option_index>
        survey_id = parts[2]
        question_id = parts[3]
        option_index = int(parts[4])

        survey = storage.get_survey(survey_id)
        if not survey or survey['status'] != 'active':
            await callback_query.answer("Этот опрос недоступен")
            return

        user_id = callback_query.from_user.id

        # Get or create user's selections for this question
        user_state = storage.get_user_state(user_id)
        selection_key = f"multi_{survey_id}_{question_id}"

        if selection_key not in user_state:
            user_state[selection_key] = []

        selections = user_state[selection_key]

        # Toggle selection
        if option_index in selections:
            selections.remove(option_index)
        else:
            selections.append(option_index)

        storage.set_user_state(user_id, selection_key, selections)

        # Update the message to show selected options
        question = next((q for q in survey['questions'] if q['id'] == question_id), None)
        if question:
            options = question['options']
            markup = InlineKeyboardMarkup(row_width=1)

            for i, option in enumerate(options):
                text = f"✅ {option}" if i in selections else option
                markup.add(InlineKeyboardButton(
                    text,
                    callback_data=f"multi_choice_{survey_id}_{question_id}_{i}"
                ))

            # Add submit button
            markup.add(InlineKeyboardButton(
                "Подтвердить выбор",
                callback_data=f"multi_submit_{survey_id}_{question_id}"
            ))

            await callback_query.message.edit_reply_markup(reply_markup=markup)

        await callback_query.answer()

    async def process_multiple_choice_submit(self, callback_query: CallbackQuery):
        """Process submission of multiple choice answers"""
        parts = callback_query.data.split('_')
        # Примерный формат: multi_submit_<survey_id>_<question_id>
        survey_id = parts[2]
        question_id = parts[3]

        survey = storage.get_survey(survey_id)
        if not survey or survey['status'] != 'active':
            await callback_query.answer("Этот опрос недоступен")
            return

        user_id = callback_query.from_user.id

        # Get user's selections
        user_state = storage.get_user_state(user_id)
        selection_key = f"multi_{survey_id}_{question_id}"
        selections = user_state.get(selection_key, [])

        if not selections:
            await callback_query.answer("Пожалуйста, выберите хотя бы один вариант")
            return

        # Record the response
        response = {
            'user_id': None if survey.get('is_anonymous') else user_id,
            'question_id': question_id,
            'answer': selections,
            'timestamp': callback_query.message.date.isoformat()
        }

        # Add or update response
        self._add_or_update_response(survey, user_id, question_id, response)
        storage.save_survey(survey_id, survey)

        # Clear user's selections
        storage.set_user_state(user_id, selection_key, None)

        await callback_query.answer("Ваши ответы записаны!")

        # Update message to show it's been submitted
        old_text = callback_query.message.text or ""
        await callback_query.message.edit_text(
            f"{old_text}\n\n✅ Ваш ответ принят!"
        )

    def _add_or_update_response(self, survey, user_id, question_id, new_response):
        """Add or update a response in the survey"""
        # For anonymous surveys, always add a new response
        if survey.get('is_anonymous'):
            survey['responses'].append(new_response)
            return

        # For non-anonymous, update existing response if any
        for i, response in enumerate(survey['responses']):
            if (response.get('user_id') == user_id and
                response.get('question_id') == question_id):
                survey['responses'][i] = new_response
                return

        # No existing response found, add new one
        survey['responses'].append(new_response)

    def process_results(self, question, responses):
        """Process results for this question type"""
        options = question['options']
        counts = [0] * len(options)

        for response in responses:
            if isinstance(response.get('answer'), list):
                for option_index in response['answer']:
                    if 0 <= option_index < len(options):
                        counts[option_index] += 1

        total_responses = len(responses)
        results = {
            'question': question['text'],
            'type': 'multiple_choice',
            'total_responses': total_responses,
            'options': []
        }

        for i, option in enumerate(options):
            percentage = (counts[i] / total_responses * 100) if total_responses > 0 else 0
            results['options'].append({
                'text': option,
                'count': counts[i],
                'percentage': round(percentage, 1)
            })

        return results

    def on_plugin_load(self):
        """Called when the plugin is loaded"""
        logger.info("Multiple choice plugin loaded")

    def on_plugin_unload(self):
        """Called when the plugin is unloaded"""
        logger.info("Multiple choice plugin unloaded")

def load_plugin():
    """Load the plugin"""
    return MultipleChoicePlugin()
