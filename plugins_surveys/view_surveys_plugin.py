"""
Плагин просмотра опросов.

Реализует возможность просматривать список опросов, фильтровать их и получать
подробную информацию.
"""

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

# Используем функции из db_manager вместо отсутствующего модуля базы данных
from core.db_manager import (
    get_all_polls,
    get_poll_id_by_name,
    get_poll_by_id,
    get_questions_by_poll,
)
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


async def get_surveys(user_id: Optional[int] = None) -> List[Dict]:
    """Возвращает все доступные опросы."""
    surveys = []
    for name in get_all_polls():
        poll_id = get_poll_id_by_name(name)
        poll = get_poll_by_id(poll_id)
        if not poll:
            continue
        surveys.append(
            {
                "id": poll_id,
                "title": poll["name"],
                "questions": get_questions_by_poll(poll_id),
                "time_limit": poll.get("time_limit"),
            }
        )
    return surveys


async def get_survey_by_id(survey_id: int) -> Optional[Dict]:
    """Получает опрос по его ID."""
    poll = get_poll_by_id(survey_id)
    if not poll:
        return None
    poll["title"] = poll.pop("name")
    poll["questions"] = get_questions_by_poll(survey_id)
    return poll


async def format_survey_info(survey: Dict) -> str:
    """Форматирует информацию об опросе для отображения."""
    info = f"<b>{survey.get('title')}</b>\n"
    info += f"Вопросов: {len(survey.get('questions', []))}\n"
    if survey.get("time_limit"):
        info += f"Завершение: {survey['time_limit']}\n"
    return info


def has_poll_ended(survey: Dict) -> bool:
    """Возвращает True, если время опроса истекло."""
    tl = survey.get("time_limit")
    if not tl:
        return False
    try:
        end_time = datetime.fromisoformat(tl)
    except (TypeError, ValueError):
        return False
    return datetime.now() > end_time


class ViewSurveysStates(StatesGroup):
    """Состояния процесса просмотра опросов"""

    Viewing = State()
    FilterMenu = State()
    ViewingDetails = State()


class ViewSurveysPlugin:
    """Плагин для просмотра опросов"""

    def __init__(self):
        self.name = "view_surveys_plugin"
        self.description = "Просмотр и управление опросами"

    async def register_handlers(self, router: Router):
        """Регистрирует все обработчики плагина"""
        router.message.register(self.cmd_view_surveys, Command("view_surveys"))
        router.callback_query.register(
            self.handle_survey_selection,
            lambda c: c.data.startswith("view_survey_"),
            StateFilter(ViewSurveysStates.Viewing),
        )
        router.callback_query.register(
            self.handle_filter_selection,
            lambda c: c.data.startswith("filter_"),
            StateFilter(ViewSurveysStates.FilterMenu),
        )
        router.callback_query.register(
            self.handle_survey_action,
            lambda c: c.data.startswith("survey_action_"),
            StateFilter(ViewSurveysStates.ViewingDetails),
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
        """Возвращает список команд плагина"""
        return [
            types.BotCommand(
                command="view_surveys",
                description="Мои опросы",
            )
        ]

    def get_keyboards(self):
        """Возвращает клавиатуры, необходимые плагину"""
        return {}

    def get_states(self):
        """Возвращает состояния, которые использует плагин"""
        return ViewSurveysStates

    async def cmd_view_surveys(self, message: types.Message, state: FSMContext):
        """Обрабатывает команду /view_surveys"""
        logger.debug(f"{message.text} from {message.from_user.id}")
        user_id = message.from_user.id
        surveys = await get_surveys(user_id=user_id)

        if not surveys:
            await message.answer("Нет доступных опросов.")
            return

        # Создаём клавиатуру со списком опросов
        builder = InlineKeyboardBuilder()
        for survey in surveys:
            status = "✅ Активен" if not has_poll_ended(survey) else "❌ Завершён"
            button_text = f"{survey['title']} ({status})"
            builder.button(
                text=button_text, callback_data=f"view_survey_{survey['id']}"
            )
        builder.button(text="🔍 Фильтр опросов", callback_data="filter_menu")
        builder.adjust(1)
        markup = builder.as_markup()
        await message.answer("Доступные опросы:", reply_markup=markup)
        await state.set_state(ViewSurveysStates.Viewing)

    async def handle_survey_selection(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Обрабатывает выбор опроса из списка"""
        survey_id = int(callback_query.data.split("_")[2])
        survey = await get_survey_by_id(survey_id)

        if not survey:
            await callback_query.answer("Опрос не найден.")
            return

        # Формируем текст с подробной информацией
        survey_info = await format_survey_info(survey)

        # Создаём кнопки действий
        builder = InlineKeyboardBuilder()

        if not has_poll_ended(survey):
            builder.button(
                text="Пройти опрос", callback_data=f"survey_action_take_{survey_id}"
            )

        builder.button(text="Назад к списку", callback_data="survey_action_back")
        builder.adjust(2)
        keyboard = builder.as_markup()

        await callback_query.message.edit_text(
            survey_info, reply_markup=keyboard, parse_mode="HTML"
        )
        await state.set_state(ViewSurveysStates.ViewingDetails)
        await callback_query.answer()

    async def handle_filter_selection(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Обрабатывает выбор фильтра для опросов"""
        user_id = callback_query.from_user.id
        filter_type = callback_query.data.split("_")[1]

        if filter_type == "menu":
            # Показываем варианты фильтра
            builder = InlineKeyboardBuilder()
            builder.button(text="Активные опросы", callback_data="filter_active")
            builder.button(text="Завершённые опросы", callback_data="filter_completed")
            builder.button(text="Все опросы", callback_data="filter_all")
            builder.button(text="Назад", callback_data="filter_back")
            builder.adjust(1)
            markup = builder.as_markup()
            await callback_query.message.edit_text(
                "Выберите вариант фильтра:", reply_markup=markup
            )
            await state.set_state(ViewSurveysStates.FilterMenu)

        elif filter_type == "back":
            # Возврат к общему списку опросов
            await self.cmd_view_surveys(callback_query.message, state)

        else:
            # Применяем выбранный фильтр
            surveys = await get_surveys(user_id=user_id)

            if filter_type == "active":
                surveys = [s for s in surveys if not has_poll_ended(s)]
            elif filter_type == "completed":
                surveys = [s for s in surveys if has_poll_ended(s)]

            # Создаём клавиатуру с отфильтрованными опросами
            builder = InlineKeyboardBuilder()

            if not surveys:
                back_builder = InlineKeyboardBuilder()
                back_builder.button(text="Назад", callback_data="filter_menu")
                back_builder.adjust(1)
                await callback_query.message.edit_text(
                    "Нет опросов, удовлетворяющих фильтру.",
                    reply_markup=back_builder.as_markup(),
                )
                return

            for survey in surveys:
                status = "✅ Активен" if not has_poll_ended(survey) else "❌ Завершён"
                button_text = f"{survey['title']} ({status})"
                builder.button(
                    text=button_text, callback_data=f"view_survey_{survey['id']}"
                )

            builder.button(text="🔍 Фильтр опросов", callback_data="filter_menu")
            builder.adjust(1)
            keyboard = builder.as_markup()

            await callback_query.message.edit_text(
                f"Опросы ({filter_type}):", reply_markup=keyboard
            )
            await state.set_state(ViewSurveysStates.Viewing)

        await callback_query.answer()

    async def handle_survey_action(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Обрабатывает действия с выбранным опросом"""
        action = callback_query.data.split("_")[2]

        if action == "back":
            # Возврат к списку опросов
            await self.cmd_view_surveys(callback_query.message, state)

        elif action == "take":
            survey_id = int(callback_query.data.split("_")[3])
            # Запускаем прохождение опроса
            # Обычно здесь происходит переход к другому плагину
            await callback_query.message.answer(f"Запускаем опрос {survey_id}...")
            # Сбрасываем состояние, чтобы другие хендлеры могли продолжить
            await state.clear()

        await callback_query.answer()


# Эту функцию использует менеджер плагинов для загрузки модуля
def load_plugin():
    """Загружает плагин"""
    return ViewSurveysPlugin()
