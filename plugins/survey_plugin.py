"""
Плагин для создания и управления опросами в Telegram-боте.
Реализует создание, редактирование и просмотр опросов.
"""

import logging
from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter
import uuid
from datetime import datetime, timedelta
import asyncio

# Импортируем модуль хранилища
try:
    from plugins.storage_plugin import storage
except ImportError:
    # Запасной вариант для тестирования
    class DummyStorage:
        def get_survey(self, survey_id): return {}
        def save_survey(self, survey_id, data): pass
        def get_all_surveys(self): return {}
        def delete_survey(self, survey_id): pass
        def get_user_state(self, user_id): return {}
        def set_user_state(self, user_id, key, value): pass
        def get_setting(self, key, default=None): return default
        def set_setting(self, key, value): pass
    storage = DummyStorage()

logger = logging.getLogger(__name__)

class SurveyStates(StatesGroup):
    """Состояния для создания и управления опросами"""
    CREATING = State()
    TITLE = State()
    DESCRIPTION = State()
    QUESTION_TYPE = State()
    QUESTION_TEXT = State()
    ADDING_OPTIONS = State()
    SCHEDULING = State()
    DEADLINE = State()
    ANONYMITY = State()
    CONFIRMATION = State()
    EDITING = State()
    EDITING_QUESTION = State()

class SurveyPlugin:
    """Плагин для создания и управления опросами"""

    def __init__(self):
        self.name = "survey_plugin"
        self.description = "Создание и управление опросами"
        self.scheduled_tasks = {}

    async def register_handlers(self, dp: Dispatcher):
        """Регистрирует все обработчики для плагина опросов"""
        # Обработчики создания опроса
        dp.message.register(
            self.cmd_create_survey,
            Command(commands=["create_survey"])
        )
        dp.message.register(
            self.cmd_create_survey,
            lambda msg: msg.text == "Создать опрос"
        )
        dp.message.register(
            self.process_title,
            StateFilter(SurveyStates.TITLE)
        )
        dp.message.register(
            self.process_description,
            StateFilter(SurveyStates.DESCRIPTION)
        )
        dp.callback_query.register(
            self.process_question_type_selection,
            lambda c: c.data.startswith('type_'),
            StateFilter(SurveyStates.QUESTION_TYPE)
        )
        dp.message.register(
            self.process_question_text,
            StateFilter(SurveyStates.QUESTION_TEXT)
        )
        dp.message.register(
            self.process_options,
            StateFilter(SurveyStates.ADDING_OPTIONS)
        )
        dp.message.register(
            self.process_deadline,
            StateFilter(SurveyStates.DEADLINE)
        )
        dp.callback_query.register(
            self.process_anonymity_selection,
            lambda c: c.data.startswith('anon_'),
            StateFilter(SurveyStates.ANONYMITY)
        )
        dp.callback_query.register(
            self.process_scheduling_selection,
            lambda c: c.data.startswith('schedule_'),
            StateFilter(SurveyStates.SCHEDULING)
        )
        dp.message.register(
            self.process_confirmation,
            StateFilter(SurveyStates.CONFIRMATION)
        )

        # Обработчики управления опросами
        dp.message.register(
            self.cmd_view_surveys,
            Command(commands=["view_surveys"])
        )
        dp.message.register(
            self.cmd_view_surveys,
            lambda msg: msg.text == "Мои опросы"
        )
        dp.callback_query.register(
            self.process_survey_action,
            lambda c: c.data.startswith('survey_')
        )
        dp.callback_query.register(
            self.process_edit_question,
            lambda c: c.data.startswith('edit_q_'),
            StateFilter(SurveyStates.EDITING)
        )
        dp.message.register(
            self.process_edited_question,
            StateFilter(SurveyStates.EDITING_QUESTION)
        )

    def get_commands(self):
        """Возвращает список команд, предоставляемых плагином"""
        return [
            types.BotCommand(command="create_survey", description="Создать новый опрос"),
            types.BotCommand(command="view_surveys", description="Просмотреть мои опросы")
        ]

    async def cmd_create_survey(self, message: types.Message, state: FSMContext):
        """Обработчик команды создания нового опроса"""
        await state.set_state(SurveyStates.TITLE)
        await state.update_data(creator_id=message.from_user.id)
        await message.answer("Введите название опроса:")

    async def process_title(self, message: types.Message, state: FSMContext):
        """Обрабатывает ввод названия опроса"""
        await state.update_data(title=message.text)
        await state.set_state(SurveyStates.DESCRIPTION)
        await message.answer("Введите описание опроса:")

    async def process_description(self, message: types.Message, state: FSMContext):
        """Обрабатывает ввод описания опроса"""
        await state.update_data(description=message.text)
        await state.set_state(SurveyStates.QUESTION_TYPE)

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("Одиночный выбор", callback_data="type_single"),
            InlineKeyboardButton("Множественный выбор", callback_data="type_multiple"),
            InlineKeyboardButton("Текстовый ответ", callback_data="type_text")
        )

        await message.answer("Выберите тип вопроса:", reply_markup=markup)

    async def process_question_type_selection(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Обрабатывает выбор типа вопроса"""
        question_type = callback_query.data.split('_')[1]

        question_types = {
            "single": "одиночный выбор",
            "multiple": "множественный выбор",
            "text": "текстовый ответ"
        }

        if question_type in question_types:
            await state.update_data(question_type=question_types[question_type])
            await state.set_state(SurveyStates.QUESTION_TEXT)

            await callback_query.message.edit_text(
                f"Выбран тип: {question_types[question_type]}\n\nВведите текст вопроса:"
            )

        await callback_query.answer()

    async def process_question_text(self, message: types.Message, state: FSMContext):
        """Обрабатывает ввод текста вопроса"""
        await state.update_data(question_text=message.text)
        data = await state.get_data()

        if data['question_type'] in ["одиночный выбор", "множественный выбор"]:
            await state.set_state(SurveyStates.ADDING_OPTIONS)
            await message.answer(
                "Введите варианты ответов, каждый с новой строки.\nВведите 'Готово', когда закончите:"
            )
        else:
            await state.set_state(SurveyStates.DEADLINE)
            await message.answer("Введите срок действия опроса в часах (например, 24):")

    async def process_options(self, message: types.Message, state: FSMContext):
        """Обрабатывает ввод вариантов ответов"""
        if message.text.lower() == "готово":
            data = await state.get_data()
            if 'options' not in data or not data['options']:
                await message.answer("Вы не добавили ни одного варианта ответа. Пожалуйста, введите варианты:")
                return

            await state.set_state(SurveyStates.DEADLINE)
            await message.answer("Введите срок действия опроса в часах (например, 24):")
        else:
            options = message.text.split('\n')
            async with state.proxy() as data:
                if 'options' not in data:
                    data['options'] = []
                data['options'].extend(options)
            await message.answer(f"Добавлено {len(options)} вариантов. Продолжайте добавлять или введите 'Готово':")

    async def process_deadline(self, message: types.Message, state: FSMContext):
        """Обрабатывает ввод срока действия опроса"""
        try:
            hours = int(message.text)
            if hours <= 0:
                await message.answer("Пожалуйста, введите положительное число часов:")
                return

            deadline = datetime.now() + timedelta(hours=hours)
            await state.update_data(deadline=deadline.isoformat())

            await state.set_state(SurveyStates.ANONYMITY)
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("Да", callback_data="anon_yes"),
                InlineKeyboardButton("Нет", callback_data="anon_no")
            )
            await message.answer("Сделать опрос анонимным?", reply_markup=markup)
        except ValueError:
            await message.answer("Пожалуйста, введите число часов:")

    async def process_anonymity_selection(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Обрабатывает выбор анонимности опроса"""
        is_anonymous = callback_query.data.split('_')[1] == "yes"
        await state.update_data(is_anonymous=is_anonymous)

        # Запрос о планировании отправки опроса
        await state.set_state(SurveyStates.SCHEDULING)
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("Сейчас", callback_data="schedule_now"),
            InlineKeyboardButton("Запланировать", callback_data="schedule_later")
        )

        anon_status = "Да" if is_anonymous else "Нет"
        await callback_query.message.edit_text(
            f"Анонимный опрос: {anon_status}\n\nКогда отправить опрос?",
            reply_markup=markup
        )

        await callback_query.answer()

    async def process_scheduling_selection(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Обрабатывает выбор способа отправки опроса (немедленно или с планированием)"""
        schedule_type = callback_query.data.split('_')[1]

        if schedule_type == "now":
            await state.update_data(scheduled=False)
            await state.set_state(SurveyStates.CONFIRMATION)

            data = await state.get_data()
            summary = self._generate_survey_summary(data)

            await callback_query.message.edit_text(
                f"{summary}\n\nДля подтверждения создания опроса введите 'Подтвердить':"
            )
        else:
            await callback_query.message.edit_text(
                "Функция планирования будет доступна в ближайшее время.\n\nОпрос будет создан для немедленной отправки.\nДля подтверждения введите 'Подтвердить':"
            )
            await state.set_state(SurveyStates.CONFIRMATION)

        await callback_query.answer()

    async def process_confirmation(self, message: types.Message, state: FSMContext):
        """Обрабатывает подтверждение создания опроса"""
        if message.text.lower() == "подтвердить":
            data = await state.get_data()
            survey_id = str(uuid.uuid4())
            survey = {
                'id': survey_id,
                'title': data['title'],
                'description': data['description'],
                'creator_id': data['creator_id'],
                'created_at': datetime.now().isoformat(),
                'deadline': data['deadline'],
                'is_anonymous': data.get('is_anonymous', False),
                'questions': [{
                    'id': str(uuid.uuid4()),
                    'text': data['question_text'],
                    'type': data['question_type'],
                    'options': data.get('options', []) if data['question_type'] != "текстовый ответ" else []
                }],
                'responses': [],
                'status': 'active'
            }

            storage.save_survey(survey_id, survey)
            self._schedule_survey_notifications(survey)
            await state.finish()
            await message.answer(f"✅ Опрос '{data['title']}' успешно создан!")
        else:
            await message.answer("Для подтверждения создания опроса введите 'Подтвердить':")

    async def cmd_view_surveys(self, message: types.Message, state: FSMContext):
        """Обработчик команды просмотра опросов"""
        user_id = message.from_user.id
        surveys = storage.get_all_surveys()
        user_surveys = {k: v for k, v in surveys.items() if v.get('creator_id') == user_id}

        if not user_surveys:
            await message.answer("У вас пока нет созданных опросов.")
            return

        for survey_id, survey in user_surveys.items():
            status = "Активен" if survey['status'] == 'active' else "Завершен"
            deadline = datetime.fromisoformat(survey['deadline'])
            remaining = (deadline - datetime.now()).total_seconds() / 3600

            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("Редактировать", callback_data=f"survey_edit_{survey_id}"),
                InlineKeyboardButton("Удалить", callback_data=f"survey_delete_{survey_id}"),
                InlineKeyboardButton("Результаты", callback_data=f"survey_results_{survey_id}")
            )

            await message.answer(
                f"📊 <b>{survey['title']}</b>\nОписание: {survey['description']}\nСтатус: {status}\nОсталось: {int(remaining)} часов\nВопросов: {len(survey['questions'])}\nОтветов: {len(survey['responses'])}",
                reply_markup=markup,
                parse_mode="HTML"
            )

    async def process_survey_action(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Обрабатывает действия с опросом (редактирование, удаление, просмотр результатов)"""
        parts = callback_query.data.split('_')
        action = parts[1]
        survey_id = parts[2]

        if action == "edit":
            survey = storage.get_survey(survey_id)
            if not survey:
                await callback_query.answer("Опрос не найден")
                return

            await state.set_state(SurveyStates.EDITING)
            await state.update_data(editing_survey_id=survey_id)

            markup = InlineKeyboardMarkup(row_width=1)
            for i, question in enumerate(survey['questions']):
                question_text = question['text']
                if len(question_text) > 30:
                    question_text = question_text[:30] + "..."
                markup.add(InlineKeyboardButton(
                    f"Вопрос {i+1}: {question_text}",
                    callback_data=f"edit_q_{question['id']}"
                ))
            markup.add(InlineKeyboardButton("Отмена", callback_data="edit_cancel"))

            await callback_query.message.answer(
                "Выберите вопрос для редактирования:",
                reply_markup=markup
            )

        elif action == "delete":
            storage.delete_survey(survey_id)
            await callback_query.message.edit_text("Опрос удален")

        elif action == "results":
            survey = storage.get_survey(survey_id)
            if not survey:
                await callback_query.answer("Опрос не найден")
                return
            results = self._generate_results(survey)
            await callback_query.message.answer(results, parse_mode="HTML")

        await callback_query.answer()

    async def process_edit_question(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Обрабатывает выбор вопроса для редактирования"""
        if callback_query.data == "edit_cancel":
            await state.finish()
            await callback_query.message.answer("Редактирование отменено")
            return

        question_id = callback_query.data.split('_')[2]
        data = await state.get_data()
        survey_id = data['editing_survey_id']
        survey = storage.get_survey(survey_id)

        question = next((q for q in survey['questions'] if q['id'] == question_id), None)
        if not question:
            await callback_query.answer("Вопрос не найден")
            return

        await state.update_data(editing_question_id=question_id)
        await state.set_state(SurveyStates.EDITING_QUESTION)

        await callback_query.message.answer(
            f"Редактирование вопроса:\nТекущий текст: {question['text']}\nТип: {question['type']}\n\nВведите новый текст вопроса:"
        )

        await callback_query.answer()

    async def process_edited_question(self, message: types.Message, state: FSMContext):
        """Обрабатывает изменённый текст вопроса"""
        data = await state.get_data()
        survey_id = data['editing_survey_id']
        question_id = data['editing_question_id']

        survey = storage.get_survey(survey_id)
        if not survey:
            await message.answer("Опрос не найден")
            await state.finish()
            return

        for question in survey['questions']:
            if question['id'] == question_id:
                question['text'] = message.text
                break

        storage.save_survey(survey_id, survey)
        await message.answer("✅ Вопрос успешно обновлен!")
        await state.finish()

    def _generate_survey_summary(self, data):
        """Генерирует сводку опроса для подтверждения"""
        summary = f"<b>Опрос: {data['title']}</b>\n"
        summary += f"Описание: {data['description']}\n"
        summary += f"Тип вопроса: {data['question_type']}\n"
        summary += f"Вопрос: {data['question_text']}\n"

        if data['question_type'] in ["одиночный выбор", "множественный выбор"]:
            summary += "\nВарианты ответов:\n"
            for i, option in enumerate(data.get('options', [])):
                summary += f"{i+1}. {option}\n"

        deadline = datetime.fromisoformat(data['deadline'])
        summary += f"\nСрок действия: до {deadline.strftime('%d.%m.%Y %H:%M')}\n"
        summary += f"Анонимный: {'Да' if data.get('is_anonymous', False) else 'Нет'}"

        return summary

    def _generate_results(self, survey):
        """Генерирует отчёт по результатам опроса"""
        results = f"<b>Результаты опроса: {survey['title']}</b>\n\n"

        for question in survey['questions']:
            results += f"<b>Вопрос:</b> {question['text']}\n"
            if question['type'] == "текстовый ответ":
                text_responses = [r['answer'] for r in survey['responses'] if r['question_id'] == question['id']]
                results += f"<b>Ответы ({len(text_responses)}):</b>\n"
                for i, response in enumerate(text_responses[:5]):
                    results += f"{i+1}. {response}\n"
                if len(text_responses) > 5:
                    results += f"...и еще {len(text_responses) - 5} ответов\n"
            else:
                options = question['options']
                counts = [0] * len(options)
                for response in survey['responses']:
                    if response['question_id'] == question['id']:
                        if question['type'] == "одиночный выбор":
                            counts[response['answer']] += 1
                        else:
                            for option_index in response['answer']:
                                counts[option_index] += 1
                total = sum(counts)
                results += f"<b>Результаты ({total} ответов):</b>\n"
                for i, option in enumerate(options):
                    percentage = (counts[i] / total * 100) if total > 0 else 0
                    results += f"{option}: {counts[i]} ({percentage:.1f}%)\n"
            results += "\n"

        return results

    def _schedule_survey_notifications(self, survey):
        """Планирует уведомления для опроса"""
        survey_id = survey['id']
        deadline = datetime.fromisoformat(survey['deadline'])

        reminder_time = deadline - timedelta(minutes=10)
        now = datetime.now()

        if reminder_time > now:
            seconds_until_reminder = (reminder_time - now).total_seconds()
            self.scheduled_tasks[f"reminder_{survey_id}"] = asyncio.create_task(
                self._send_reminder(survey_id, seconds_until_reminder)
            )

        seconds_until_close = (deadline - now).total_seconds()
        if seconds_until_close > 0:
            self.scheduled_tasks[f"close_{survey_id}"] = asyncio.create_task(
                self._close_survey(survey_id, seconds_until_close)
            )

    async def _send_reminder(self, survey_id, delay_seconds):
        """Отправляет напоминание о скором завершении опроса"""
        await asyncio.sleep(delay_seconds)
        survey = storage.get_survey(survey_id)
        if not survey or survey['status'] != 'active':
            return
        logger.info(f"Напоминание: Опрос '{survey['title']}' закрывается через 10 минут!")

    async def _close_survey(self, survey_id, delay_seconds):
        """Закрывает опрос по истечении срока"""
        await asyncio.sleep(delay_seconds)
        survey = storage.get_survey(survey_id)
        if not survey or survey['status'] != 'active':
            return
        survey['status'] = 'closed'
        storage.save_survey(survey_id, survey)
        results = self._generate_results(survey)
        logger.info(f"Опрос '{survey['title']}' закрыт. Результаты:\n{results}")

    def on_plugin_load(self):
        """Вызывается при загрузке плагина"""
        logger.info("Плагин опросов загружен")
        surveys = storage.get_all_surveys()
        for survey_id, survey in surveys.items():
            if survey['status'] == 'active':
                self._schedule_survey_notifications(survey)

    def on_plugin_unload(self):
        """Вызывается при выгрузке плагина"""
        for task in self.scheduled_tasks.values():
            task.cancel()
        logger.info("Плагин опросов выгружен")

def load_plugin():
    """Загружает плагин"""
    return SurveyPlugin()