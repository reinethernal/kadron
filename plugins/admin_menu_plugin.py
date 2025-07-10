"""
Плагин административного меню для Telegram-бота.

Обеспечивает функциональность меню администратора с поддержкой состояний.
"""

import logging
from dotenv import load_dotenv
from utils.env_utils import parse_admin_ids


from plugin_manager import PluginManager
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter

# Fallback plugin classes in case dependencies are missing
from .survey_plugin import SurveyPlugin
from .export_plugin import ExportPlugin
from .test_mode_plugin import TestModePlugin
from .survey_templates_plugin import SurveyTemplatesPlugin
from .roles_plugin import RolesPlugin

# Загружаем переменные из .env файла
load_dotenv()

logger = logging.getLogger(__name__)


class AdminMenuStates(StatesGroup):
    """Состояния для административного меню"""

    MAIN_MENU = State()  # Главное меню
    SURVEYS_MENU = State()  # Меню опросов
    ANALYTICS_MENU = State()  # Меню аналитики
    SETTINGS_MENU = State()  # Меню настроек


class AdminMenuPlugin:
    """Плагин административного меню"""

    def __init__(self, plugin_manager: PluginManager):
        self.name = "admin_menu_plugin"
        self.description = "Функциональность административного меню"
        # Загружаем admin_ids из переменной окружения
        self.admin_ids = parse_admin_ids()
        logger.debug(f"Parsed admin_ids: {self.admin_ids}")
        self.plugin_manager = plugin_manager

        # Resolve plugin dependencies using helper
        self.survey_plugin = self._get_or_create("survey_plugin", SurveyPlugin)
        self.export_plugin = self._get_or_create("export_plugin", ExportPlugin)
        self.test_mode_plugin = self._get_or_create("test_mode_plugin", TestModePlugin)
        self.templates_plugin = self._get_or_create(
            "survey_templates_plugin", SurveyTemplatesPlugin
        )
        self.roles_plugin = self._get_or_create("roles_plugin", RolesPlugin)

    def _get_or_create(self, plugin_name: str, cls):
        """Fetches a plugin from PluginManager or raises if missing."""
        plugin = self.plugin_manager.get_plugin(plugin_name)
        if plugin:
            return plugin
        logger.error(
            f"Dependency '{plugin_name}' not found in PluginManager. "
            f"'{self.name}' requires all dependencies to be loaded."
        )
        raise RuntimeError(
            f"Dependency '{plugin_name}' must be loaded via PluginManager"
        )

    async def register_handlers(self, router: Router):
        """Регистрирует все обработчики для плагина"""
        router.callback_query.register(
            self.admin_menu_callback,
            lambda c: c.data == "admin_menu",
        )
        router.callback_query.register(
            self.handle_main_menu,
            lambda c: c.data in {"admin_surveys", "admin_analytics", "admin_settings"},
            StateFilter(AdminMenuStates.MAIN_MENU),
        )
        router.callback_query.register(
            self.handle_back,
            lambda c: c.data == "admin_back",
            StateFilter(
                AdminMenuStates.SURVEYS_MENU,
                AdminMenuStates.ANALYTICS_MENU,
                AdminMenuStates.SETTINGS_MENU,
            ),
        )
        router.callback_query.register(
            self.handle_surveys_menu,
            lambda c: c.data
            in {
                "surveys_create",
                "surveys_my",
                "surveys_templates",
                "surveys_settings",
            },
            StateFilter(AdminMenuStates.SURVEYS_MENU),
        )
        router.callback_query.register(
            self.handle_analytics_menu,
            lambda c: c.data
            in {
                "analytics_export",
                "analytics_stats",
                "analytics_activity",
                "analytics_ratings",
            },
            StateFilter(AdminMenuStates.ANALYTICS_MENU),
        )
        router.callback_query.register(
            self.handle_settings_menu,
            lambda c: c.data
            in {
                "settings_general",
                "settings_notifications",
                "settings_access",
                "settings_testmode",
            },
            StateFilter(AdminMenuStates.SETTINGS_MENU),
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
        """Административное меню теперь открывается через кнопку, поэтому команды отсутствуют."""
        return []

    def get_keyboards(self):
        """Возвращает словарь инлайн-клавиатур для различных меню"""

        def btn(text: str, cb: str):
            try:
                return InlineKeyboardButton(text=text, callback_data=cb)
            except TypeError:
                # Fallback for tests where InlineKeyboardButton is mocked
                return types.KeyboardButton(text)

        # Главное меню
        main = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    btn("📊 Опросы", "admin_surveys"),
                    btn("📈 Аналитика", "admin_analytics"),
                ],
                [btn("⚙ Настройки", "admin_settings")],
            ]
        )

        # Меню опросов
        surveys = InlineKeyboardMarkup(
            inline_keyboard=[
                [btn("Создать опрос", "surveys_create")],
                [btn("Мои опросы", "surveys_my")],
                [btn("Шаблоны вопросов", "surveys_templates")],
                [btn("Настройки опросов", "surveys_settings")],
                [btn("🔙 Назад", "admin_back")],
            ]
        )

        # Меню аналитики
        analytics = InlineKeyboardMarkup(
            inline_keyboard=[
                [btn("Экспорт данных", "analytics_export")],
                [btn("Статистика опросов", "analytics_stats")],
                [btn("Активность группы", "analytics_activity")],
                [btn("Рейтинги", "analytics_ratings")],
                [btn("🔙 Назад", "admin_back")],
            ]
        )

        # Меню настроек
        settings = InlineKeyboardMarkup(
            inline_keyboard=[
                [btn("Общие настройки", "settings_general")],
                [btn("Настройки уведомлений", "settings_notifications")],
                [btn("Управление доступом", "settings_access")],
                [btn("Тестовый режим", "settings_testmode")],
                [btn("🔙 Назад", "admin_back")],
            ]
        )

        return {
            "admin_main": main,
            "admin_surveys": surveys,
            "admin_analytics": analytics,
            "admin_settings": settings,
        }

    async def cmd_admin_menu(self, message: types.Message, state: FSMContext):
        """Открывает меню администратора по команде"""
        logger.debug(f"{message.text} from {message.from_user.id}")
        if message.from_user.id not in self.admin_ids:
            await message.answer("У вас нет доступа к меню администратора.")
            return
        await state.set_state(AdminMenuStates.MAIN_MENU)
        await message.answer(
            "Главное меню администратора:",
            reply_markup=self.get_keyboards()["admin_main"],
        )

    async def admin_menu_callback(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Открывает админ меню по нажатию кнопки"""
        if callback_query.from_user.id not in self.admin_ids:
            await callback_query.answer("Нет доступа")
            return
        await state.set_state(AdminMenuStates.MAIN_MENU)
        await callback_query.message.answer(
            "Главное меню администратора:",
            reply_markup=self.get_keyboards()["admin_main"],
        )
        await callback_query.answer()

    async def handle_main_menu(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Обрабатывает выбор пункта главного меню"""
        data = getattr(callback_query, "data", getattr(callback_query, "text", ""))
        if data == "admin_surveys":
            await state.set_state(AdminMenuStates.SURVEYS_MENU)
            await callback_query.message.edit_text(
                "Меню управления опросами:",
                reply_markup=self.get_keyboards()["admin_surveys"],
            )
        elif data == "admin_analytics":
            await state.set_state(AdminMenuStates.ANALYTICS_MENU)
            await callback_query.message.edit_text(
                "Меню аналитики:",
                reply_markup=self.get_keyboards()["admin_analytics"],
            )
        elif data == "admin_settings":
            await state.set_state(AdminMenuStates.SETTINGS_MENU)
            await callback_query.message.edit_text(
                "Меню настроек:",
                reply_markup=self.get_keyboards()["admin_settings"],
            )
        if hasattr(callback_query, "data"):
            await callback_query.answer()

    async def handle_surveys_menu(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Выбор пунктов в меню опросов"""
        data = getattr(callback_query, "data", getattr(callback_query, "text", ""))
        if data == "surveys_create":
            await self.survey_plugin.cmd_create_survey(callback_query.message, state)
        elif data == "surveys_my":
            await self.survey_plugin.cmd_view_surveys(callback_query.message, state)
        elif data == "surveys_templates":
            await self.templates_plugin.cmd_list_templates(callback_query.message)
        elif data == "surveys_settings":
            await callback_query.message.answer("Функция в разработке")
        if hasattr(callback_query, "data"):
            await callback_query.answer()

    async def handle_analytics_menu(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Выбор пунктов в меню аналитики"""
        data = getattr(callback_query, "data", getattr(callback_query, "text", ""))
        if data == "analytics_export":
            await self.export_plugin.cmd_export(callback_query.message)
        elif data == "analytics_stats":
            await callback_query.message.answer("Функция в разработке")
        elif data == "analytics_activity":
            await callback_query.message.answer("Функция в разработке")
        elif data == "analytics_ratings":
            await callback_query.message.answer("Функция в разработке")
        if hasattr(callback_query, "data"):
            await callback_query.answer()

    async def handle_settings_menu(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Выбор пунктов в меню настроек"""
        data = getattr(callback_query, "data", getattr(callback_query, "text", ""))
        if data == "settings_testmode":
            await self.test_mode_plugin.cmd_test_mode(callback_query.message, state)
        elif data == "settings_access":
            await self.roles_plugin.cmd_roles(callback_query.message, state)
        elif data in {"settings_general", "settings_notifications"}:
            await callback_query.message.answer("Функция в разработке")
        if hasattr(callback_query, "data"):
            await callback_query.answer()

    async def handle_back(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Обрабатывает кнопку 'Назад'"""
        await state.set_state(AdminMenuStates.MAIN_MENU)
        await callback_query.message.edit_text(
            "Главное меню администратора:",
            reply_markup=self.get_keyboards()["admin_main"],
        )
        if hasattr(callback_query, "data"):
            await callback_query.answer()


def load_plugin(plugin_manager: PluginManager):
    """Загружает плагин"""
    return AdminMenuPlugin(plugin_manager=plugin_manager)
