"""
Плагин административного меню для Telegram-бота.

Обеспечивает функциональность меню администратора с поддержкой состояний.
"""

import logging
from dotenv import load_dotenv
from utils.env_utils import parse_admin_ids
from typing import Optional

from plugin_manager import PluginManager
from aiogram import Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter

# Fallback plugin classes in case dependencies are missing
from plugins.survey_plugin import SurveyPlugin
from plugins.export_plugin import ExportPlugin
from plugins.test_mode_plugin import TestModePlugin
from plugins.survey_templates_plugin import SurveyTemplatesPlugin
from plugins.roles_plugin import RolesPlugin

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

    def __init__(self, plugin_manager: Optional[PluginManager] = None):
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
        self.templates_plugin = self._get_or_create("survey_templates_plugin", SurveyTemplatesPlugin)
        self.roles_plugin = self._get_or_create("roles_plugin", RolesPlugin)

    def _get_or_create(self, plugin_name: str, cls):
        """Fetches a plugin from PluginManager or creates a fallback instance."""
        plugin = None
        if self.plugin_manager:
            plugin = self.plugin_manager.get_plugin(plugin_name)
        if plugin:
            return plugin
        logger.warning(
            f"Dependency '{plugin_name}' not found in PluginManager. "
            f"Creating new {cls.__name__} instance."
        )
        return cls()

    async def register_handlers(self, dp: Dispatcher):
        """Регистрирует все обработчики для плагина"""
        dp.message.register(self.cmd_admin_menu, Command(commands=["admin"]))
        dp.message.register(
            self.handle_main_menu,
            lambda msg: msg.text in ["📊 Опросы", "📈 Аналитика", "⚙ Настройки"],
            StateFilter(AdminMenuStates.MAIN_MENU),
        )
        dp.message.register(
            self.handle_back,
            lambda msg: msg.text == "🔙 Назад",
            StateFilter(
                AdminMenuStates.SURVEYS_MENU,
                AdminMenuStates.ANALYTICS_MENU,
                AdminMenuStates.SETTINGS_MENU,
            ),
        )
        dp.message.register(
            self.handle_surveys_menu,
            lambda msg: msg.text
            in [
                "Создать опрос",
                "Мои опросы",
                "Шаблоны вопросов",
                "Настройки опросов",
            ],
            StateFilter(AdminMenuStates.SURVEYS_MENU),
        )
        dp.message.register(
            self.handle_analytics_menu,
            lambda msg: msg.text
            in [
                "Статистика опросов",
                "Экспорт данных",
                "Активность группы",
                "Рейтинги",
            ],
            StateFilter(AdminMenuStates.ANALYTICS_MENU),
        )
        dp.message.register(
            self.handle_settings_menu,
            lambda msg: msg.text
            in [
                "Общие настройки",
                "Настройки уведомлений",
                "Управление доступом",
                "Тестовый режим",
            ],
            StateFilter(AdminMenuStates.SETTINGS_MENU),
        )

    def get_commands(self):
        """Возвращает список команд, предоставляемых плагином"""
        return [
            types.BotCommand(command="admin", description="Открыть меню администратора")
        ]

    def get_keyboards(self):
        """Возвращает словарь клавиатур для различных меню"""
        if not self.plugin_manager:
            return {
                "admin_main": ReplyKeyboardMarkup(
                    keyboard=[
                        [
                            KeyboardButton(text="📊 Опросы"),
                            KeyboardButton(text="📈 Аналитика"),
                        ],
                        [KeyboardButton(text="⚙ Настройки")],
                    ],
                    resize_keyboard=True,
                    one_time_keyboard=False,
                ),
                "admin_surveys": ReplyKeyboardMarkup(
                    keyboard=[
                        [
                            KeyboardButton(text="Создать опрос"),
                            KeyboardButton(text="Мои опросы"),
                        ],
                        [
                            KeyboardButton(text="Шаблоны вопросов"),
                            KeyboardButton(text="Настройки опросов"),
                        ],
                        [KeyboardButton(text="🔙 Назад")],
                    ],
                    resize_keyboard=True,
                    one_time_keyboard=False,
                ),
                "admin_analytics": ReplyKeyboardMarkup(
                    keyboard=[
                        [
                            KeyboardButton(text="Статистика опросов"),
                            KeyboardButton(text="Экспорт данных"),
                        ],
                        [
                            KeyboardButton(text="Активность группы"),
                            KeyboardButton(text="Рейтинги"),
                        ],
                        [KeyboardButton(text="🔙 Назад")],
                    ],
                    resize_keyboard=True,
                    one_time_keyboard=False,
                ),
                "admin_settings": ReplyKeyboardMarkup(
                    keyboard=[
                        [
                            KeyboardButton(text="Общие настройки"),
                            KeyboardButton(text="Настройки уведомлений"),
                        ],
                        [
                            KeyboardButton(text="Управление доступом"),
                            KeyboardButton(text="Тестовый режим"),
                        ],
                        [KeyboardButton(text="🔙 Назад")],
                    ],
                    resize_keyboard=True,
                    one_time_keyboard=False,
                ),
            }

        plugin_commands = self.plugin_manager.get_plugin_commands()
        buttons = []
        for cmd_list in plugin_commands.values():
            for cmd in cmd_list:
                text = getattr(cmd, "description", None) or getattr(cmd, "command", "")
                if text:
                    buttons.append(KeyboardButton(text=text))

        rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        rows.append([KeyboardButton(text="🔙 Назад")])

        return {
            "admin_main": ReplyKeyboardMarkup(
                keyboard=[
                    [
                        KeyboardButton(text="📊 Опросы"),
                        KeyboardButton(text="📈 Аналитика"),
                    ],
                    [KeyboardButton(text="⚙ Настройки")],
                ],
                resize_keyboard=True,
                one_time_keyboard=False,
            ),
            "admin_surveys": ReplyKeyboardMarkup(
                keyboard=rows,
                resize_keyboard=True,
                one_time_keyboard=False,
            ),
            "admin_analytics": ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔙 Назад")]],
                resize_keyboard=True,
                one_time_keyboard=False,
            ),
            "admin_settings": ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔙 Назад")]],
                resize_keyboard=True,
                one_time_keyboard=False,
            ),
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

    async def handle_main_menu(self, message: types.Message, state: FSMContext):
        """Обрабатывает выбор пункта главного меню"""
        if message.text == "📊 Опросы":
            await state.set_state(AdminMenuStates.SURVEYS_MENU)
            await message.answer(
                "Меню управления опросами:",
                reply_markup=self.get_keyboards()["admin_surveys"],
            )
        elif message.text == "📈 Аналитика":
            await state.set_state(AdminMenuStates.ANALYTICS_MENU)
            await message.answer(
                "Меню аналитики:", reply_markup=self.get_keyboards()["admin_analytics"]
            )
        elif message.text == "⚙ Настройки":
            await state.set_state(AdminMenuStates.SETTINGS_MENU)
            await message.answer(
                "Меню настроек:", reply_markup=self.get_keyboards()["admin_settings"]
            )

    async def handle_surveys_menu(self, message: types.Message, state: FSMContext):
        """Выбор пунктов в меню опросов"""
        if message.text == "Создать опрос":
            await self.survey_plugin.cmd_create_survey(message, state)
        elif message.text == "Мои опросы":
            await self.survey_plugin.cmd_view_surveys(message, state)
        elif message.text == "Шаблоны вопросов":
            await self.templates_plugin.cmd_list_templates(message)
        elif message.text == "Настройки опросов":
            await message.answer("Функция в разработке")

    async def handle_analytics_menu(self, message: types.Message, state: FSMContext):
        """Выбор пунктов в меню аналитики"""
        if message.text == "Экспорт данных":
            await self.export_plugin.cmd_export(message)
        elif message.text == "Статистика опросов":
            await message.answer("Функция в разработке")
        elif message.text == "Активность группы":
            await message.answer("Функция в разработке")
        elif message.text == "Рейтинги":
            await message.answer("Функция в разработке")

    async def handle_settings_menu(self, message: types.Message, state: FSMContext):
        """Выбор пунктов в меню настроек"""
        if message.text == "Тестовый режим":
            await self.test_mode_plugin.cmd_test_mode(message, state)
        elif message.text == "Управление доступом":
            await self.roles_plugin.cmd_roles(message, state)
        else:
            await message.answer("Функция в разработке")

    async def handle_back(self, message: types.Message, state: FSMContext):
        """Обрабатывает кнопку 'Назад'"""
        await state.set_state(AdminMenuStates.MAIN_MENU)
        await message.answer(
            "Главное меню администратора:",
            reply_markup=self.get_keyboards()["admin_main"],
        )


def load_plugin(plugin_manager: Optional[PluginManager] = None):
    """Загружает плагин"""
    return AdminMenuPlugin(plugin_manager=plugin_manager)
