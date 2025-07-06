"""
Плагин текстовых ответов для Telegram‑бота.

Реализует тип вопроса, предполагающий текстовый ответ, и обрабатывает его
отображение и ввод пользователем.
"""

from aiogram import Dispatcher, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter  # Добавляем фильтр состояния
import logging
from core.db_manager import add_response
from plugins.response_mixin import ResponseMixin

# Импорт хранилища из storage_plugin
try:
    from plugins.storage_plugin import storage
except ImportError:
    # Запасной вариант для тестирования
    class DummyStorage:
        def get_survey(self, survey_id): return {}
        def save_survey(self, survey_id, data): pass
    storage = DummyStorage()

logger = logging.getLogger(__name__)

class TextAnswerStates(StatesGroup):
    """Состояния обработки текстового ответа"""
    WAITING_FOR_ANSWER = State()

class TextAnswerPlugin(ResponseMixin):
    """Плагин для вопросов с текстовым ответом"""
    
    def __init__(self):
        self.name = "text_answer_plugin"
        self.description = "Тип вопроса - текстовый ответ"
    
    async def register_handlers(self, dp: Dispatcher):
        """Регистрирует все обработчики плагина"""
        dp.callback_query.register(
            self.start_text_answer,
            lambda c: c.data.startswith('text_answer_')
        )
        dp.message.register(
            self.process_text_answer,
            StateFilter(TextAnswerStates.WAITING_FOR_ANSWER)  # Убираем 'state='
        )
    
    def get_commands(self):
        """Возвращает список команд плагина"""
        return []
    
    def get_question_type(self):
        """Возвращает идентификатор типа вопроса"""
        return "text_answer"
    
    def get_question_type_name(self):
        """Возвращает название типа вопроса"""
        return "Текстовый ответ"
    
    def create_question_form(self, question_data=None):
        """Возвращает описание формы для создания такого вопроса"""
        return {
            'type': 'text_answer',
            'name': 'Текстовый ответ',
            'fields': [
                {'name': 'text', 'label': 'Текст вопроса', 'type': 'text', 'required': True}
            ]
        }
    
    def render_question(self, question, survey_id):
        """Отображает вопрос для ответа"""
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Ответить",
            callback_data=f"text_answer_{survey_id}_{question['id']}"
        )
        markup = builder.as_markup()
        
        return {
            'text': question['text'],
            'markup': markup
        }
    
    async def start_text_answer(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Запускает процесс ввода текстового ответа"""
        parts = callback_query.data.split('_')
        survey_id = parts[2]
        question_id = parts[3]
        
        survey = storage.get_survey(survey_id)
        if not survey or survey['status'] != 'active':
            await callback_query.answer("Этот опрос недоступен")
            return
        
        # Сохраняем информацию о вопросе в состоянии
        await state.update_data(
            survey_id=survey_id,
            question_id=question_id
        )
        
        await state.set_state(TextAnswerStates.WAITING_FOR_ANSWER)
        await callback_query.message.reply(
            "Пожалуйста, введите ваш ответ на вопрос. Отправьте сообщение с текстом:"
        )
        await callback_query.answer()
    
    async def process_text_answer(self, message: types.Message, state: FSMContext):
        """Обрабатывает введённый текстовый ответ"""
        data = await state.get_data()
        survey_id = data.get('survey_id')
        question_id = data.get('question_id')
        
        if not survey_id or not question_id:
            await message.reply("Произошла ошибка. Пожалуйста, начните заново.")
            await state.clear()
            return
        
        survey = storage.get_survey(survey_id)
        if not survey or survey['status'] != 'active':
            await message.reply("Этот опрос больше не доступен.")
            await state.clear()
            return
        
        user_id = message.from_user.id
        
        # Записываем ответ
        response = {
            'user_id': None if survey['is_anonymous'] else user_id,
            'question_id': question_id,
            'answer': message.text,
            'timestamp': message.date.isoformat()
        }

        # Добавляем либо обновляем ответ
        self._add_or_update_response(survey, user_id, question_id, response)
        add_response(survey_id, question_id, response['user_id'], message.text, message.date)
        storage.save_survey(survey_id, survey)
        
        await message.reply("✅ Ваш ответ записан! Спасибо за участие.")
        await state.clear()
    
    
    def process_results(self, question, responses):
        """Обрабатывает результаты для этого типа вопроса"""
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
        """Вызывается при загрузке плагина"""
        logger.info("Плагин текстовых ответов загружен")
    
    def on_plugin_unload(self):
        """Вызывается при выгрузке плагина"""
        logger.info("Плагин текстовых ответов выгружен")

def load_plugin():
    """Загружает плагин"""
    return TextAnswerPlugin()