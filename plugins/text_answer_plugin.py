"""
Text Answer Plugin for Telegram Bot

This plugin provides text answer question type functionality.
It handles rendering and processing text answer questions.
"""

from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter  # Добавляем фильтр состояния
import logging

# Import storage from storage_plugin
try:
    from plugins.storage_plugin import storage
except ImportError:
    # Fallback for testing
    class DummyStorage:
        def get_survey(self, survey_id): return {}
        def save_survey(self, survey_id, data): pass
    storage = DummyStorage()

logger = logging.getLogger(__name__)

class TextAnswerStates(StatesGroup):
    """States for text answer handling"""
    WAITING_FOR_ANSWER = State()

class TextAnswerPlugin:
    """Plugin for text answer question type"""
    
    def __init__(self):
        self.name = "text_answer_plugin"
        self.description = "Text answer question type"
    
    async def register_handlers(self, dp: Dispatcher):
        """Register all handlers for this plugin"""
        dp.callback_query.register(
            self.start_text_answer,
            lambda c: c.data.startswith('text_answer_')
        )
        dp.message.register(
            self.process_text_answer,
            StateFilter(TextAnswerStates.WAITING_FOR_ANSWER)  # Убираем 'state='
        )
    
    def get_commands(self):
        """Return a list of commands this plugin provides"""
        return []
    
    def get_question_type(self):
        """Return the question type identifier"""
        return "text_answer"
    
    def get_question_type_name(self):
        """Return the human-readable question type name"""
        return "Текстовый ответ"
    
    def create_question_form(self, question_data=None):
        """Return form for creating this question type"""
        return {
            'type': 'text_answer',
            'name': 'Текстовый ответ',
            'fields': [
                {'name': 'text', 'label': 'Текст вопроса', 'type': 'text', 'required': True}
            ]
        }
    
    def render_question(self, question, survey_id):
        """Render the question for users to answer"""
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(
            "Ответить",
            callback_data=f"text_answer_{survey_id}_{question['id']}"
        ))
        
        return {
            'text': question['text'],
            'markup': markup
        }
    
    async def start_text_answer(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Start the text answer process"""
        parts = callback_query.data.split('_')
        survey_id = parts[2]
        question_id = parts[3]
        
        survey = storage.get_survey(survey_id)
        if not survey or survey['status'] != 'active':
            await callback_query.answer("Этот опрос недоступен")
            return
        
        # Store the question info in state
        await state.update_data(
            survey_id=survey_id,
            question_id=question_id
        )
        
        await TextAnswerStates.WAITING_FOR_ANSWER.set()
        await callback_query.message.reply(
            "Пожалуйста, введите ваш ответ на вопрос. Отправьте сообщение с текстом:"
        )
        await callback_query.answer()
    
    async def process_text_answer(self, message: types.Message, state: FSMContext):
        """Process the text answer"""
        data = await state.get_data()
        survey_id = data.get('survey_id')
        question_id = data.get('question_id')
        
        if not survey_id or not question_id:
            await message.reply("Произошла ошибка. Пожалуйста, начните заново.")
            await state.finish()
            return
        
        survey = storage.get_survey(survey_id)
        if not survey or survey['status'] != 'active':
            await message.reply("Этот опрос больше не доступен.")
            await state.finish()
            return
        
        user_id = message.from_user.id
        
        # Record the response
        response = {
            'user_id': None if survey['is_anonymous'] else user_id,
            'question_id': question_id,
            'answer': message.text,
            'timestamp': message.date.isoformat()
        }
        
        # Add or update response
        self._add_or_update_response(survey, user_id, question_id, response)
        storage.save_survey(survey_id, survey)
        
        await message.reply("✅ Ваш ответ записан! Спасибо за участие.")
        await state.finish()
    
    def _add_or_update_response(self, survey, user_id, question_id, new_response):
        """Add or update a response in the survey"""
        # For anonymous surveys, always add a new response
        if survey['is_anonymous']:
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
        results = {
            'question': question['text'],
            'type': 'text_answer',
            'total_responses': len(responses),
            'answers': []
        }
        
        for response in responses:
            results['answers'].append({
                'text': response['answer'],
                'user_id': response.get('user_id'),
                'timestamp': response.get('timestamp')
            })
        
        return results
    
    def on_plugin_load(self):
        """Called when the plugin is loaded"""
        logger.info("Text answer plugin loaded")
    
    def on_plugin_unload(self):
        """Called when the plugin is unloaded"""
        logger.info("Text answer plugin unloaded")

def load_plugin():
    """Load the plugin"""
    return TextAnswerPlugin()