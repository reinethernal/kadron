from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
import copy

# Импорт хранилища
try:
    from .storage_plugin import storage
except ImportError:

    class DummyStorage:
        def get_survey(self, survey_id):
            return {}

        def save_survey(self, survey_id, data):
            pass

        def get_setting(self, key, default=None):
            return default

        def set_setting(self, key, value):
            pass

        def get_all_surveys(self):
            return {}

    storage = DummyStorage()

logger = logging.getLogger(__name__)


class TestModeStates(StatesGroup):
    SELECTING_SURVEY = State()
    TESTING_SURVEY = State()


class TestModePlugin:
    def __init__(self):
        self.name = "test_mode_plugin"
        self.description = "Тестовый режим для опросов"
        self.test_surveys = {}

    async def register_handlers(self, router: Router):
        router.message.register(self.cmd_test_mode, Command("test_mode"))
        router.callback_query.register(
            self.handle_survey_selection, lambda c: c.data.startswith("test_survey_")
        )
        router.callback_query.register(
            self.handle_test_action, lambda c: c.data.startswith("test_action_")
        )
        router.callback_query.register(
            self.handle_test_response, lambda c: c.data.startswith("test_response_")
        )

    async def unregister_handlers(self, router: Router):
        for attr in dir(router):
            event = getattr(router, attr)
            handlers = getattr(event, "handlers", None)
            if handlers is None:
                continue
            handlers[:] = [
                h
                for h in handlers
                if getattr(getattr(h, "callback", h), "__self__", None) is not self
            ]

    def get_commands(self):
        # В aiogram 3.x конструкция BotCommand теперь требует именованных аргументов:
        return [
            types.BotCommand(
                command="test_mode", description="Тестовый режим для опросов"
            )
        ]

    async def cmd_test_mode(self, message: types.Message, state: FSMContext):
        logger.debug(f"{message.text} from {message.from_user.id}")
        user_id = message.from_user.id
        # Получаем все опросы пользователя
        all_surveys = storage.get_all_surveys()
        user_surveys = {
            survey_id: survey
            for survey_id, survey in all_surveys.items()
            if survey.get("creator_id") == user_id
        }
        if not user_surveys:
            await message.answer("У вас нет опросов для тестирования.")
            return
        builder = InlineKeyboardBuilder()
        for survey_id, survey in user_surveys.items():
            builder.button(
                text=survey.get("title", "Без названия"),
                callback_data=f"test_survey_{survey_id}",
            )
        builder.adjust(1)
        markup = builder.as_markup()
        await message.answer(
            "🧪 Тестовый режим\n\nВыберите опрос для тестирования:", reply_markup=markup
        )
        await state.set_state(TestModeStates.SELECTING_SURVEY)

    async def handle_survey_selection(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        survey_id = callback_query.data.split("_")[2]
        survey = storage.get_survey(survey_id)
        if not survey:
            await callback_query.answer("Опрос не найден.")
            await state.clear()
            return
        # Создаём копию опроса для тестирования
        test_survey = copy.deepcopy(survey)
        test_survey["responses"] = []
        test_id = f"test_{survey_id}_{callback_query.from_user.id}"
        self.test_surveys[test_id] = test_survey
        await state.update_data(test_id=test_id)
        builder = InlineKeyboardBuilder()
        builder.button(
            text="▶️ Начать тестирование", callback_data=f"test_action_start_{test_id}"
        )
        builder.button(
            text="📊 Просмотреть результаты",
            callback_data=f"test_action_results_{test_id}",
        )
        builder.button(
            text="❌ Завершить тестирование", callback_data="test_action_exit"
        )
        builder.adjust(1)
        markup = builder.as_markup()
        await callback_query.message.edit_text(
            f"🧪 Тестовый режим: {test_survey.get('title')}\n\nВ тестовом режиме вы можете пройти опрос и просмотреть результаты без влияния на реальные данные.",
            reply_markup=markup,
        )
        await state.set_state(TestModeStates.TESTING_SURVEY)
        await callback_query.answer()

    async def handle_test_action(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        parts = callback_query.data.split("_")
        action = parts[2]
        if action == "exit":
            await callback_query.message.edit_text("Тестовый режим завершен.")
            await state.clear()
            await callback_query.answer()
            return
        test_id = parts[3]
        test_survey = self.test_surveys.get(test_id)
        if not test_survey:
            await callback_query.answer("Тестовый опрос не найден.")
            await state.clear()
            return
        if action == "start":
            await self.start_test_survey(callback_query, test_survey, test_id)
        elif action == "results":
            await self.show_test_results(callback_query, test_survey)
        await callback_query.answer()

    async def start_test_survey(
        self, callback_query: types.CallbackQuery, test_survey, test_id
    ):
        questions = test_survey.get("questions", [])
        if not questions:
            await callback_query.message.edit_text("Этот опрос не содержит вопросов.")
            return
        await self.show_test_question(callback_query.message, test_survey, test_id, 0)

    async def show_test_question(self, message, test_survey, test_id, question_index):
        questions = test_survey.get("questions", [])
        if question_index >= len(questions):
            builder = InlineKeyboardBuilder()
            builder.button(
                text="📊 Просмотреть результаты",
                callback_data=f"test_action_results_{test_id}",
            )
            builder.button(
                text="🔄 Пройти заново", callback_data=f"test_action_start_{test_id}"
            )
            builder.button(
                text="❌ Завершить тестирование", callback_data="test_action_exit"
            )
            builder.adjust(1)
            markup = builder.as_markup()
            await message.edit_text(
                "✅ Тестирование опроса завершено!\n\nВы можете просмотреть результаты или пройти опрос заново.",
                reply_markup=markup,
            )
            return
        question = questions[question_index]
        question_type = question.get("type", "unknown")
        if question_type == "single_choice":
            builder = InlineKeyboardBuilder()
            for i, option in enumerate(question.get("options", [])):
                builder.button(
                    text=option,
                    callback_data=f"test_response_single_{test_id}_{question_index}_{i}",
                )
            builder.adjust(1)
            markup = builder.as_markup()
            await message.edit_text(
                f"Вопрос {question_index+1}/{len(questions)}:\n\n{question.get('text')}\n\nВыберите один вариант:",
                reply_markup=markup,
            )
        elif question_type == "multiple_choice":
            builder = InlineKeyboardBuilder()
            for i, option in enumerate(question.get("options", [])):
                builder.button(
                    text=option,
                    callback_data=f"test_response_multi_{test_id}_{question_index}_{i}",
                )
            builder.button(
                text="✅ Подтвердить выбор",
                callback_data=f"test_response_submit_{test_id}_{question_index}",
            )
            builder.adjust(1)
            markup = builder.as_markup()
            await message.edit_text(
                f"Вопрос {question_index+1}/{len(questions)}:\n\n{question.get('text')}\n\nВыберите один или несколько вариантов:",
                reply_markup=markup,
            )
        elif question_type == "text_answer":
            builder = InlineKeyboardBuilder()
            test_answers = [
                "Тестовый ответ 1",
                "Это пример текстового ответа",
                "Тестирование функциональности",
            ]
            for i, answer in enumerate(test_answers):
                builder.button(
                    text=f"Ответ {i+1}",
                    callback_data=f"test_response_text_{test_id}_{question_index}_{i}",
                )
            builder.adjust(1)
            markup = builder.as_markup()
            await message.edit_text(
                f"Вопрос {question_index+1}/{len(questions)}:\n\n{question.get('text')}\n\nВ тестовом режиме выберите один из предопределенных ответов:",
                reply_markup=markup,
            )

    async def handle_test_response(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        parts = callback_query.data.split("_")
        response_type = parts[2]
        test_id = parts[3]
        question_index = int(parts[4])
        test_survey = self.test_surveys.get(test_id)
        if not test_survey:
            await callback_query.answer("Тестовый опрос не найден.")
            await state.clear()
            return
        questions = test_survey.get("questions", [])
        if question_index >= len(questions):
            await callback_query.answer("Вопрос не найден.")
            return
        question = questions[question_index]
        if response_type == "single":
            option_index = int(parts[5])
            response = {
                "user_id": callback_query.from_user.id,
                "question_id": question.get("id"),
                "answer": option_index,
                "timestamp": callback_query.message.date.isoformat(),
            }
            test_survey["responses"].append(response)
            await self.show_test_question(
                callback_query.message, test_survey, test_id, question_index + 1
            )
        elif response_type == "multi":
            option_index = int(parts[5])
            state_data = await state.get_data()
            selections_key = f"test_selections_{test_id}_{question_index}"
            selections = state_data.get(selections_key, [])
            if option_index in selections:
                selections.remove(option_index)
            else:
                selections.append(option_index)
            await state.update_data({selections_key: selections})
            builder = InlineKeyboardBuilder()
            for i, option in enumerate(question.get("options", [])):
                text = f"✅ {option}" if i in selections else option
                builder.button(
                    text=text,
                    callback_data=f"test_response_multi_{test_id}_{question_index}_{i}",
                )
            builder.button(
                text="✅ Подтвердить выбор",
                callback_data=f"test_response_submit_{test_id}_{question_index}",
            )
            builder.adjust(1)
            markup = builder.as_markup()
            await callback_query.message.edit_reply_markup(reply_markup=markup)
        elif response_type == "submit":
            state_data = await state.get_data()
            selections_key = f"test_selections_{test_id}_{question_index}"
            selections = state_data.get(selections_key, [])
            response = {
                "user_id": callback_query.from_user.id,
                "question_id": question.get("id"),
                "answer": selections,
                "timestamp": callback_query.message.date.isoformat(),
            }
            test_survey["responses"].append(response)
            await state.update_data({selections_key: []})
            await self.show_test_question(
                callback_query.message, test_survey, test_id, question_index + 1
            )
        elif response_type == "text":
            answer_index = int(parts[5])
            test_answers = [
                "Тестовый ответ 1",
                "Это пример текстового ответа",
                "Тестирование функциональности",
            ]
            selected_answer = (
                test_answers[answer_index]
                if answer_index < len(test_answers)
                else "Тестовый ответ"
            )
            response = {
                "user_id": callback_query.from_user.id,
                "question_id": question.get("id"),
                "answer": selected_answer,
                "timestamp": callback_query.message.date.isoformat(),
            }
            test_survey["responses"].append(response)
            await self.show_test_question(
                callback_query.message, test_survey, test_id, question_index + 1
            )
        await callback_query.answer()

    async def show_test_results(self, callback_query: types.CallbackQuery, test_survey):
        questions = test_survey.get("questions", [])
        responses = test_survey.get("responses", [])
        if not responses:
            await callback_query.message.edit_text(
                "Нет данных для отображения. Пройдите опрос в тестовом режиме."
            )
            return
        results = ["📊 Результаты тестирования:\n"]
        for question in questions:
            question_id = question.get("id")
            question_type = question.get("type")
            question_responses = [
                r for r in responses if r.get("question_id") == question_id
            ]
            results.append(f"\n📝 {question.get('text')}")
            results.append(f"Тип: {question_type}")
            results.append(f"Ответов: {len(question_responses)}")
            if question_type == "single_choice":
                options = question.get("options", [])
                counts = [0] * len(options)
                for response in question_responses:
                    answer = response.get("answer")
                    if isinstance(answer, int) and 0 <= answer < len(options):
                        counts[answer] += 1
                for i, option in enumerate(options):
                    percentage = (
                        (counts[i] / len(question_responses) * 100)
                        if question_responses
                        else 0
                    )
                    results.append(f"  - {option}: {counts[i]} ({percentage:.1f}%)")
            elif question_type == "multiple_choice":
                options = question.get("options", [])
                counts = [0] * len(options)
                for response in question_responses:
                    answer = response.get("answer", [])
                    for option_index in answer:
                        if 0 <= option_index < len(options):
                            counts[option_index] += 1
                for i, option in enumerate(options):
                    percentage = (
                        (counts[i] / len(question_responses) * 100)
                        if question_responses
                        else 0
                    )
                    results.append(f"  - {option}: {counts[i]} ({percentage:.1f}%)")
            elif question_type == "text_answer":
                results.append("Текстовые ответы:")
                for i, response in enumerate(question_responses):
                    answer = response.get("answer", "")
                    results.append(f"  {i+1}. {answer}")
        builder = InlineKeyboardBuilder()
        builder.button(
            text="🔄 Пройти заново",
            callback_data=callback_query.data.replace("results", "start"),
        )
        builder.button(
            text="❌ Завершить тестирование", callback_data="test_action_exit"
        )
        builder.adjust(1)
        markup = builder.as_markup()
        results_text = "\n".join(results)
        if len(results_text) > 4000:
            chunks = []
            current_chunk = []
            current_length = 0
            for line in results:
                if current_length + len(line) + 1 > 4000:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [line]
                    current_length = len(line)
                else:
                    current_chunk.append(line)
                    current_length += len(line) + 1
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await callback_query.message.edit_text(chunk, reply_markup=None)
                else:
                    await callback_query.message.reply(chunk)
            await callback_query.message.reply(
                "Выберите действие:", reply_markup=markup
            )
        else:
            await callback_query.message.edit_text(results_text, reply_markup=markup)

    def on_plugin_load(self):
        logger.info("Плагин тестового режима загружен")

    def on_plugin_unload(self):
        self.test_surveys.clear()
        logger.info("Плагин тестового режима выгружен")


def load_plugin():
    return TestModePlugin()
