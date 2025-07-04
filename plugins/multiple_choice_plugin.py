"""
Плагин множественного выбора для Telegram‑бота (aiogram 3.x).

Реализует тип вопроса с выбором нескольких вариантов и обрабатывает его
отображение и ответы пользователей.
"""

import logging

from aiogram import Dispatcher
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import CallbackQuery

# Поправленные импорты для хранилища
try:
    from plugins.storage_plugin import storage
except ImportError:
    # Запасной вариант для тестов
    class DummyStorage:
        def get_survey(self, survey_id): return {}
        def save_survey(self, survey_id, data): pass
        def get_user_state(self, user_id): return {}
        def set_user_state(self, user_id, key, value): pass
    storage = DummyStorage()

logger = logging.getLogger(__name__)

class MultipleChoicePlugin:
    """Плагин для вопросов с множественным выбором"""

    def __init__(self):
        self.name = "multiple_choice_plugin"
        self.description = "Multiple choice question type"

    async def register_handlers(self, dp: Dispatcher):
        """Регистрирует обработчики плагина (стиль aiogram 3.x)"""
        dp.callback_query.register(
            self.process_multiple_choice_selection,
            lambda c: c.data.startswith('multi_choice_')
        )
        dp.callback_query.register(
            self.process_multiple_choice_submit,
            lambda c: c.data.startswith('multi_submit_')
        )

    def get_commands(self):
        """Возвращает список команд плагина"""
        return []

    def get_question_type(self):
        """Возвращает идентификатор типа вопроса"""
        return "multiple_choice"

    def get_question_type_name(self):
        """Возвращает название типа вопроса"""
        return "Множественный выбор"

    def create_question_form(self, question_data=None):
        """Возвращает описание формы для создания такого вопроса"""
        return {
            'type': 'multiple_choice',
            'name': 'Множественный выбор',
            'fields': [
                {'name': 'text', 'label': 'Текст вопроса', 'type': 'text', 'required': True},
                {'name': 'options', 'label': 'Варианты ответов (по одному в строке)', 'type': 'textarea', 'required': True}
            ]
        }

    def render_question(self, question, survey_id):
        """Отрисовывает вопрос для ответа пользователя"""
        builder = InlineKeyboardBuilder()

        for i, option in enumerate(question['options']):
            builder.button(
                text=option,
                callback_data=f"multi_choice_{survey_id}_{question['id']}_{i}"
            )

        builder.button(
            text="Подтвердить выбор",
            callback_data=f"multi_submit_{survey_id}_{question['id']}"
        )
        builder.adjust(1)
        markup = builder.as_markup()

        return {
            'text': question['text'] + "\n\nВыберите один или несколько вариантов:",
            'markup': markup
        }

    async def process_multiple_choice_selection(self, callback_query: CallbackQuery):
        """Обрабатывает выбор пользователя в вопросе с множественным выбором"""
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

        # Получаем или создаём выбор пользователя для данного вопроса
        user_state = storage.get_user_state(user_id)
        selection_key = f"multi_{survey_id}_{question_id}"

        if selection_key not in user_state:
            user_state[selection_key] = []

        selections = user_state[selection_key]

        # Переключаем выбор
        if option_index in selections:
            selections.remove(option_index)
        else:
            selections.append(option_index)

        storage.set_user_state(user_id, selection_key, selections)

        # Обновляем сообщение, чтобы показать выбранные варианты
        question = next((q for q in survey['questions'] if q['id'] == question_id), None)
        if question:
            options = question['options']
            builder = InlineKeyboardBuilder()

            for i, option in enumerate(options):
                text = f"✅ {option}" if i in selections else option
                builder.button(
                    text=text,
                    callback_data=f"multi_choice_{survey_id}_{question_id}_{i}"
                )

            # Добавляем кнопку подтверждения
            builder.button(
                text="Подтвердить выбор",
                callback_data=f"multi_submit_{survey_id}_{question_id}"
            )
            builder.adjust(1)
            markup = builder.as_markup()

            await callback_query.message.edit_reply_markup(reply_markup=markup)

        await callback_query.answer()

    async def process_multiple_choice_submit(self, callback_query: CallbackQuery):
        """Обрабатывает отправку ответов множественного выбора"""
        parts = callback_query.data.split('_')
        # Примерный формат: multi_submit_<survey_id>_<question_id>
        survey_id = parts[2]
        question_id = parts[3]

        survey = storage.get_survey(survey_id)
        if not survey or survey['status'] != 'active':
            await callback_query.answer("Этот опрос недоступен")
            return

        user_id = callback_query.from_user.id

        # Получаем выбор пользователя
        user_state = storage.get_user_state(user_id)
        selection_key = f"multi_{survey_id}_{question_id}"
        selections = user_state.get(selection_key, [])

        if not selections:
            await callback_query.answer("Пожалуйста, выберите хотя бы один вариант")
            return

        # Сохраняем ответ
        response = {
            'user_id': None if survey.get('is_anonymous') else user_id,
            'question_id': question_id,
            'answer': selections,
            'timestamp': callback_query.message.date.isoformat()
        }

        # Добавляем или обновляем ответ
        self._add_or_update_response(survey, user_id, question_id, response)
        storage.save_survey(survey_id, survey)

        # Очищаем выбор пользователя
        storage.set_user_state(user_id, selection_key, None)

        await callback_query.answer("Ваши ответы записаны!")

        # Обновляем сообщение, что ответ принят
        old_text = callback_query.message.text or ""
        await callback_query.message.edit_text(
            f"{old_text}\n\n✅ Ваш ответ принят!"
        )

    def _add_or_update_response(self, survey, user_id, question_id, new_response):
        """Добавляет или обновляет ответ в опросе"""
        # Для анонимных опросов всегда добавляем новый ответ
        if survey.get('is_anonymous'):
            survey['responses'].append(new_response)
            return

        # Для неанонимных опросов обновляем существующий ответ, если есть
        for i, response in enumerate(survey['responses']):
            if (response.get('user_id') == user_id and
                response.get('question_id') == question_id):
                survey['responses'][i] = new_response
                return

        # Если ответа ещё нет, добавляем новый
        survey['responses'].append(new_response)

    def process_results(self, question, responses):
        """Обрабатывает результаты для этого типа вопроса"""
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
        """Вызывается при загрузке плагина"""
        logger.info("Плагин множественного выбора загружен")

    def on_plugin_unload(self):
        """Вызывается при выгрузке плагина"""
        logger.info("Плагин множественного выбора выгружен")

def load_plugin():
    """Загружает плагин"""
    return MultipleChoicePlugin()
