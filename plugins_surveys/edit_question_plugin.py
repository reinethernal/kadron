"""
Плагин редактирования вопросов.

Позволяет администраторам изменять текст вопросов, варианты ответов и другие
свойства уже созданных опросов.
"""

import logging
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Используем функции db_manager вместо устаревших импортов базы данных
from core.db_manager import (
    DATABASE,
    get_all_polls,
    get_poll_id_by_name,
    get_poll_by_id,
    get_questions_by_poll,
)
import sqlite3
from dotenv import load_dotenv
from utils.env_utils import parse_admin_ids
from utils import remove_plugin_handlers
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

load_dotenv()
ADMIN_IDS = parse_admin_ids()


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    return user_id in ADMIN_IDS


async def get_surveys(creator_id: Optional[int] = None) -> List[Dict]:
    """Возвращает список всех опросов."""
    surveys = []
    for name in get_all_polls():
        poll_id = get_poll_id_by_name(name)
        poll = get_poll_by_id(poll_id)
        if not poll:
            continue
        poll_data = {
            "id": poll_id,
            "title": poll["name"],
            "questions": get_questions_by_poll(poll_id),
            "time_limit": poll.get("time_limit"),
        }
        surveys.append(poll_data)
    return surveys


async def get_survey_by_id(survey_id: int) -> Optional[Dict]:
    """Получает опрос по его ID."""
    poll = get_poll_by_id(survey_id)
    if not poll:
        return None
    poll["title"] = poll.pop("name")
    poll["questions"] = get_questions_by_poll(survey_id)
    return poll


async def update_question(survey_id: int, question_index: int, question: Dict) -> bool:
    """Обновляет вопрос в базе данных."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM questions WHERE poll_id = ? ORDER BY id LIMIT 1 OFFSET ?",
        (survey_id, question_index),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    question_id = row[0]
    options_str = (
        ",".join(question.get("options", [])) if question.get("options") else None
    )
    cursor.execute(
        "UPDATE questions SET text = ?, type = ?, options = ? WHERE id = ?",
        (question.get("text"), question.get("type"), options_str, question_id),
    )
    conn.commit()
    conn.close()
    return True


class EditQuestionStates(StatesGroup):
    """Состояния процесса редактирования вопросов"""

    SelectSurvey = State()
    SelectQuestion = State()
    EditQuestionText = State()
    EditQuestionOptions = State()
    AddOption = State()
    RemoveOption = State()
    ConfirmChanges = State()


class EditQuestionPlugin:
    """Плагин для редактирования вопросов в опросах"""

    def __init__(self):
        self.name = "edit_question_plugin"
        self.description = "Редактировать вопросы в существующих опросах"

    async def register_handlers(self, router: Router):
        """Регистрирует все обработчики плагина"""
        router.message.register(
            self.cmd_edit_question,
            Command("edit_question"),
            lambda msg: is_admin(msg.from_user.id),
        )

        router.callback_query.register(
            self.handle_survey_selection,
            lambda c: c.data.startswith("edit_survey_"),
            StateFilter(EditQuestionStates.SelectSurvey),
        )

        router.callback_query.register(
            self.handle_question_selection,
            lambda c: c.data.startswith("edit_question_"),
            StateFilter(EditQuestionStates.SelectQuestion),
        )

        router.callback_query.register(
            self.handle_edit_action,
            lambda c: c.data.startswith("edit_action_"),
            StateFilter(
                EditQuestionStates.SelectQuestion,
                EditQuestionStates.EditQuestionText,
                EditQuestionStates.EditQuestionOptions,
                EditQuestionStates.ConfirmChanges,
            ),
        )

        router.message.register(
            self.process_question_text, StateFilter(EditQuestionStates.EditQuestionText)
        )

        router.message.register(
            self.process_new_option, StateFilter(EditQuestionStates.AddOption)
        )

        router.callback_query.register(
            self.handle_remove_option,
            lambda c: c.data.startswith("remove_option_"),
            StateFilter(EditQuestionStates.RemoveOption),
        )

    async def unregister_handlers(self, router: Router):
        remove_plugin_handlers(self, router)

    def get_commands(self):
        """Возвращает список команд плагина"""
        return [
            types.BotCommand(
                command="edit_question",
                description="Настройки опросов",
            )
        ]

    def get_keyboards(self):
        """Возвращает клавиатуры, необходимые плагину"""
        return {}

    def get_states(self):
        """Возвращает состояния, используемые плагином"""
        return EditQuestionStates

    async def cmd_edit_question(self, message: types.Message, state: FSMContext):
        """Обрабатывает команду /edit_question"""
        logger.debug(f"{message.text} from {message.from_user.id}")
        user_id = message.from_user.id

        # Получаем опросы, созданные этим администратором
        surveys = await get_surveys(creator_id=user_id)

        if not surveys:
            await message.answer("У вас нет опросов для редактирования.")
            return

        builder = InlineKeyboardBuilder()

        for survey in surveys:
            builder.button(
                text=survey["title"], callback_data=f"edit_survey_{survey['id']}"
            )

        builder.adjust(1)
        markup = builder.as_markup()
        await message.answer(
            "Выберите опрос для редактирования вопросов:", reply_markup=markup
        )
        await state.set_state(EditQuestionStates.SelectSurvey)

    async def handle_survey_selection(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Обрабатывает выбор опроса для редактирования"""
        survey_id = int(callback_query.data.split("_")[2])
        survey = await get_survey_by_id(survey_id)

        if not survey:
            await callback_query.answer("Опрос не найден.")
            return

        # Сохраняем выбранный опрос в состоянии
        await state.update_data(selected_survey=survey)

        # Получаем вопросы выбранного опроса
        questions = survey.get("questions", [])

        if not questions:
            builder = InlineKeyboardBuilder()
            builder.button(text="Назад", callback_data="edit_action_back_to_surveys")
            builder.adjust(1)
            await callback_query.message.edit_text(
                "У этого опроса нет вопросов для редактирования.",
                reply_markup=builder.as_markup(),
            )
            return

        # Создаём клавиатуру с вопросами
        builder = InlineKeyboardBuilder()

        for i, question in enumerate(questions):
            builder.button(
                text=f"Q{i+1}: {question['text'][:30]}...",
                callback_data=f"edit_question_{i}",
            )

        builder.button(text="Назад", callback_data="edit_action_back_to_surveys")
        builder.adjust(1)
        markup = builder.as_markup()

        await callback_query.message.edit_text(
            f"Выберите вопрос для редактирования из опроса '{survey['title']}':",
            reply_markup=markup,
        )
        await state.set_state(EditQuestionStates.SelectQuestion)
        await callback_query.answer()

    async def handle_question_selection(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Обрабатывает выбор вопроса для редактирования"""
        question_index = int(callback_query.data.split("_")[2])

        # Получаем опрос из состояния
        state_data = await state.get_data()
        survey = state_data.get("selected_survey")

        if not survey or question_index >= len(survey.get("questions", [])):
            await callback_query.answer("Вопрос не найден.")
            return

        question = survey["questions"][question_index]

        # Сохраняем выбранный вопрос в состоянии
        await state.update_data(
            selected_question=question, question_index=question_index
        )

        # Показываем детали вопроса и варианты редактирования
        await self.show_question_edit_menu(callback_query.message, question)
        await callback_query.answer()

    async def show_question_edit_menu(self, message: types.Message, question: dict):
        """Отображает меню редактирования для вопроса"""
        # Формируем текст вопроса
        question_text = question["text"]
        question_type = question["type"]

        details = f"<b>Вопрос:</b> {question_text}\n<b>Тип:</b> {question_type}\n"

        if "options" in question and question["options"]:
            details += "\n<b>Варианты:</b>\n"
            for i, option in enumerate(question["options"]):
                details += f"{i+1}. {option}\n"

        # Создаём кнопки редактирования
        builder = InlineKeyboardBuilder()
        builder.button(text="Изменить текст вопроса", callback_data="edit_action_text")
        builder.button(
            text="Редактировать варианты", callback_data="edit_action_options"
        )
        builder.button(
            text="Назад к вопросам", callback_data="edit_action_back_to_questions"
        )
        builder.adjust(1)
        keyboard = builder.as_markup()

        await message.edit_text(details, reply_markup=keyboard, parse_mode="HTML")

    async def handle_edit_action(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Обрабатывает действия редактирования вопроса"""
        action = callback_query.data.split("_")[2]

        if action == "text":
            builder = InlineKeyboardBuilder()
            builder.button(text="Отмена", callback_data="edit_action_cancel")
            builder.adjust(1)
            await callback_query.message.edit_text(
                "Введите новый текст вопроса:", reply_markup=builder.as_markup()
            )
            await state.set_state(EditQuestionStates.EditQuestionText)

        elif action == "options":
            # Показываем меню редактирования вариантов
            state_data = await state.get_data()
            question = state_data.get("selected_question")

            builder = InlineKeyboardBuilder()
            builder.button(
                text="Добавить вариант", callback_data="edit_action_add_option"
            )
            builder.button(
                text="Удалить вариант", callback_data="edit_action_remove_option"
            )
            builder.button(text="Назад", callback_data="edit_action_back")
            builder.adjust(1)
            keyboard = builder.as_markup()

            options_text = "Текущие варианты:\n"
            if "options" in question and question["options"]:
                for i, option in enumerate(question["options"]):
                    options_text += f"{i+1}. {option}\n"
            else:
                options_text += "Варианты отсутствуют."

            await callback_query.message.edit_text(options_text, reply_markup=keyboard)
            await state.set_state(EditQuestionStates.EditQuestionOptions)

        elif action == "add_option":
            builder = InlineKeyboardBuilder()
            builder.button(text="Отмена", callback_data="edit_action_cancel_option")
            builder.adjust(1)
            await callback_query.message.edit_text(
                "Введите текст нового варианта:", reply_markup=builder.as_markup()
            )
            await state.set_state(EditQuestionStates.AddOption)

        elif action == "remove_option":
            # Меню удаления варианта
            state_data = await state.get_data()
            question = state_data.get("selected_question")

            if not question.get("options"):
                builder = InlineKeyboardBuilder()
                builder.button(text="Назад", callback_data="edit_action_back")
                builder.adjust(1)
                await callback_query.message.edit_text(
                    "У этого вопроса нет вариантов для удаления.",
                    reply_markup=builder.as_markup(),
                )
                return

            builder = InlineKeyboardBuilder()

            for i, option in enumerate(question["options"]):
                builder.button(
                    text=f"Удалить: {option}", callback_data=f"remove_option_{i}"
                )

            builder.button(text="Отмена", callback_data="edit_action_cancel_option")
            builder.adjust(1)
            await callback_query.message.edit_text(
                "Выберите вариант для удаления:", reply_markup=builder.as_markup()
            )
            await state.set_state(EditQuestionStates.RemoveOption)

        elif action == "back":
            # Возврат к деталям вопроса
            state_data = await state.get_data()
            question = state_data.get("selected_question")
            await self.show_question_edit_menu(callback_query.message, question)

        elif action == "back_to_questions":
            # Возврат к выбору вопроса
            await self.handle_survey_selection(callback_query, state)

        elif action == "back_to_surveys":
            # Возврат к выбору опроса
            await self.cmd_edit_question(callback_query.message, state)

        elif action == "cancel":
            # Отмена редактирования и возврат к деталям вопроса
            state_data = await state.get_data()
            question = state_data.get("selected_question")
            await self.show_question_edit_menu(callback_query.message, question)

        elif action == "cancel_option":
            # Отмена редактирования вариантов и возврат в меню опций
            # Создаём новый callback с действием options
            await self.handle_edit_action(
                types.CallbackQuery(
                    id=callback_query.id,
                    from_user=callback_query.from_user,
                    chat_instance=callback_query.chat_instance,
                    message=callback_query.message,
                    data="edit_action_options",
                ),
                state,
            )

        elif action == "save":
            # Сохраняем изменения вопроса
            state_data = await state.get_data()
            survey = state_data.get("selected_survey")
            question = state_data.get("selected_question")
            question_index = state_data.get("question_index")

            # Обновляем вопрос в базе данных
            survey["questions"][question_index] = question
            # Обновляем вопрос непосредственно в базе данных
            success = await update_question(survey["id"], question_index, question)

            if success:
                builder = InlineKeyboardBuilder()
                builder.button(
                    text="Назад к вопросам",
                    callback_data="edit_action_back_to_questions",
                )
                builder.adjust(1)
                await callback_query.message.edit_text(
                    "Вопрос успешно обновлён!", reply_markup=builder.as_markup()
                )
            else:
                builder = InlineKeyboardBuilder()
                builder.button(text="Назад", callback_data="edit_action_back")
                builder.adjust(1)
                await callback_query.message.edit_text(
                    "Не удалось обновить вопрос. Попробуйте ещё раз.",
                    reply_markup=builder.as_markup(),
                )

        await callback_query.answer()

    async def process_question_text(self, message: types.Message, state: FSMContext):
        """Обрабатывает ввод нового текста вопроса"""
        new_text = message.text.strip()

        if not new_text:
            await message.answer(
                "Текст вопроса не может быть пустым. Попробуйте ещё раз."
            )
            return

        # Обновляем текст вопроса в состоянии
        state_data = await state.get_data()
        question = state_data.get("selected_question")
        question["text"] = new_text

        await state.update_data(selected_question=question)

        # Показываем подтверждение
        builder = InlineKeyboardBuilder()
        builder.button(text="Сохранить", callback_data="edit_action_save")
        builder.button(text="Отмена", callback_data="edit_action_cancel")
        builder.adjust(2)
        keyboard = builder.as_markup()

        await message.answer(
            f"Текст вопроса обновлён:\n\n{new_text}\n\nСохранить изменения?",
            reply_markup=keyboard,
        )
        await state.set_state(EditQuestionStates.ConfirmChanges)

    async def process_new_option(self, message: types.Message, state: FSMContext):
        """Обрабатывает ввод нового варианта"""
        new_option = message.text.strip()

        if not new_option:
            await message.answer(
                "Текст варианта не может быть пустым. Попробуйте ещё раз."
            )
            return

        # Обновляем варианты в состоянии
        state_data = await state.get_data()
        question = state_data.get("selected_question")

        if "options" not in question:
            question["options"] = []

        question["options"].append(new_option)
        await state.update_data(selected_question=question)

        # Показываем подтверждение
        builder = InlineKeyboardBuilder()
        builder.button(text="Сохранить", callback_data="edit_action_save")
        builder.button(text="Добавить ещё", callback_data="edit_action_add_option")
        builder.button(text="Отмена", callback_data="edit_action_cancel")
        builder.adjust(2)
        keyboard = builder.as_markup()

        options_text = "Обновлённые варианты:\n"
        for i, option in enumerate(question["options"]):
            options_text += f"{i+1}. {option}\n"

        await message.answer(
            f"{options_text}\n\nСохранить изменения или добавить ещё один вариант?",
            reply_markup=keyboard,
        )
        await state.set_state(EditQuestionStates.ConfirmChanges)

    async def handle_remove_option(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Обрабатывает удаление варианта"""
        option_index = int(callback_query.data.split("_")[2])

        # Обновляем варианты в состоянии
        state_data = await state.get_data()
        question = state_data.get("selected_question")

        if "options" in question and 0 <= option_index < len(question["options"]):
            removed_option = question["options"].pop(option_index)
            await state.update_data(selected_question=question)

            # Показываем подтверждение
            builder = InlineKeyboardBuilder()
            builder.button(text="Сохранить", callback_data="edit_action_save")
            builder.button(
                text="Удалить ещё", callback_data="edit_action_remove_option"
            )
            builder.button(text="Отмена", callback_data="edit_action_cancel")
            builder.adjust(2)
            keyboard = builder.as_markup()

            options_text = "Обновлённые варианты:\n"
            if question["options"]:
                for i, option in enumerate(question["options"]):
                    options_text += f"{i+1}. {option}\n"
            else:
                options_text += "Вариантов больше нет."

            await callback_query.message.edit_text(
                f"Удалён вариант: {removed_option}\n\n{options_text}\n\nСохранить изменения или удалить ещё один вариант?",
                reply_markup=keyboard,
            )
            await state.set_state(EditQuestionStates.ConfirmChanges)
        else:
            await callback_query.answer("Некорректный номер варианта.")


# Эту функцию использует менеджер плагинов для загрузки модуля
def load_plugin():
    """Загружает плагин"""
    return EditQuestionPlugin()
