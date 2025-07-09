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
from aiogram.filters import Command, StateFilter

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
        router.message.register(self.cmd_admin_menu, Command(commands=["admin"]))
        router.callback_query.register(
            self.handle_main_menu,
            lambda c: c.data
            in {"admin_surveys", "admin_analytics", "admin_settings"},
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
        """Возвращает список команд, предоставляемых плагином"""
        return [
            types.BotCommand(command="admin", description="Открыть меню администратора")
        ]

    def get_keyboards(self):
        """Возвращает словарь инлайн-клавиатур для различных меню"""

        # Главное меню
        main = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📊 Опросы", callback_data="admin_surveys"),
                    InlineKeyboardButton(text="📈 Аналитика", callback_data="admin_analytics"),
                ],
                [InlineKeyboardButton(text="⚙ Настройки", callback_data="admin_settings")],
            ]
        )

        # Меню опросов
        surveys = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Создать опрос", callback_data="surveys_create")],
                [InlineKeyboardButton(text="Мои опросы", callback_data="surveys_my")],
                [InlineKeyboardButton(text="Шаблоны вопросов", callback_data="surveys_templates")],
                [InlineKeyboardButton(text="Настройки опросов", callback_data="surveys_settings")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
            ]
        )

        # Меню аналитики
        analytics = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Экспорт данных", callback_data="analytics_export")],
                [InlineKeyboardButton(text="Статистика опросов", callback_data="analytics_stats")],
                [InlineKeyboardButton(text="Активность группы", callback_data="analytics_activity")],
                [InlineKeyboardButton(text="Рейтинги", callback_data="analytics_ratings")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
            ]
        )

        # Меню настроек
        settings = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Общие настройки", callback_data="settings_general")],
                [InlineKeyboardButton(text="Настройки уведомлений", callback_data="settings_notifications")],
                [InlineKeyboardButton(text="Управление доступом", callback_data="settings_access")],
                [InlineKeyboardButton(text="Тестовый режим", callback_data="settings_testmode")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
            ]
        )

        return {
            "admin_main": main,
            "admin_surveys": surveys,
            "admin_analytics": analytics,
            "admin_settings": settings,
        }

    async def cmd_admin_menu(self, message: types.Message, state: FSMContext):
        """Обрабатывает команду /admin"""
        logger.debug(f"{message.text} from {message.from_user.id}")
        if message.from_user.id not in self.admin_ids:
            await message.answer("У вас нет доступа к меню администратора.")
            return
        await state.set_state(AdminMenuStates.MAIN_MENU)
        await message.answer(
            "Главное меню администратора:",
            reply_markup=self.get_keyboards()["admin_main"],
        )

    async def handle_main_menu(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Обрабатывает выбор пункта главного меню"""
        if callback_query.data == "admin_surveys":
            await state.set_state(AdminMenuStates.SURVEYS_MENU)
            await callback_query.message.edit_text(
                "Меню управления опросами:",
                reply_markup=self.get_keyboards()["admin_surveys"],
            )
        elif callback_query.data == "admin_analytics":
            await state.set_state(AdminMenuStates.ANALYTICS_MENU)
            await callback_query.message.edit_text(
                "Меню аналитики:",
                reply_markup=self.get_keyboards()["admin_analytics"],
            )
        elif callback_query.data == "admin_settings":
            await state.set_state(AdminMenuStates.SETTINGS_MENU)
            await callback_query.message.edit_text(
                "Меню настроек:",
                reply_markup=self.get_keyboards()["admin_settings"],
            )
        await callback_query.answer()

    async def handle_surveys_menu(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Выбор пунктов в меню опросов"""
        if callback_query.data == "surveys_create":
            await self.survey_plugin.cmd_create_survey(callback_query.message, state)
        elif callback_query.data == "surveys_my":
            await self.survey_plugin.cmd_view_surveys(callback_query.message, state)
        elif callback_query.data == "surveys_templates":
            await self.templates_plugin.cmd_list_templates(callback_query.message)
        elif callback_query.data == "surveys_settings":
            await callback_query.message.answer("Функция в разработке")
        await callback_query.answer()

    async def handle_analytics_menu(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Выбор пунктов в меню аналитики"""
        if callback_query.data == "analytics_export":
            await self.export_plugin.cmd_export(callback_query.message)
        elif callback_query.data == "analytics_stats":
            await callback_query.message.answer("Функция в разработке")
        elif callback_query.data == "analytics_activity":
            await callback_query.message.answer("Функция в разработке")
        elif callback_query.data == "analytics_ratings":
            await callback_query.message.answer("Функция в разработке")
        await callback_query.answer()

    async def handle_settings_menu(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Выбор пунктов в меню настроек"""
        if callback_query.data == "settings_testmode":
            await self.test_mode_plugin.cmd_test_mode(callback_query.message, state)
        elif callback_query.data == "settings_access":
            await self.roles_plugin.cmd_roles(callback_query.message, state)
        elif callback_query.data in {"settings_general", "settings_notifications"}:
            await callback_query.message.answer("Функция в разработке")
        await callback_query.answer()

    async def handle_back(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Обрабатывает кнопку 'Назад'"""
        await state.set_state(AdminMenuStates.MAIN_MENU)
        await callback_query.message.edit_text(
            "Главное меню администратора:",
            reply_markup=self.get_keyboards()["admin_main"],
        )
        await callback_query.answer()


def load_plugin(plugin_manager: PluginManager):
    """Загружает плагин"""
    return AdminMenuPlugin(plugin_manager=plugin_manager)
