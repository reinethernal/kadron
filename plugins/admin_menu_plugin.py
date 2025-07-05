"""
Плагин административного меню для Telegram-бота.

Обеспечивает функциональность меню администратора с поддержкой состояний.
"""

import logging
import os
import re
from dotenv import load_dotenv
from aiogram import Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter

# Загружаем переменные из .env файла
load_dotenv()

logger = logging.getLogger(__name__)

class AdminMenuStates(StatesGroup):
    """Состояния для административного меню"""
    MAIN_MENU = State()         # Главное меню
    SURVEYS_MENU = State()      # Меню опросов
    ANALYTICS_MENU = State()    # Меню аналитики
    SETTINGS_MENU = State()     # Меню настроек

class AdminMenuPlugin:
    """Плагин административного меню"""
    
    def __init__(self):
        self.name = "admin_menu_plugin"
        self.description = "Функциональность административного меню"
        # Загружаем admin_ids из переменной окружения с помощью regex
        ids = re.findall(r"\d+", os.getenv("ADMIN_IDS", ""))
        self.admin_ids = [int(x) for x in ids]
        logger.debug(f"Parsed admin_ids: {self.admin_ids}")
        # Экземпляры вспомогательных плагинов
        from plugins.survey_plugin import SurveyPlugin
        from plugins.export_plugin import ExportPlugin
        from plugins.test_mode_plugin import TestModePlugin
        from plugins.survey_templates_plugin import SurveyTemplatesPlugin
        from plugins.roles_plugin import RolesPlugin

        self.survey_plugin = SurveyPlugin()
        self.export_plugin = ExportPlugin()
        self.test_mode_plugin = TestModePlugin()
        self.templates_plugin = SurveyTemplatesPlugin()
        self.roles_plugin = RolesPlugin()
    
    async def register_handlers(self, dp: Dispatcher):
        """Регистрирует все обработчики для плагина"""
        dp.message.register(
            self.cmd_admin_menu,
            Command(commands=["admin"])
        )
        dp.message.register(
            self.handle_main_menu,
            lambda msg: msg.text in ["📊 Опросы", "📈 Аналитика", "⚙ Настройки"],
            StateFilter(AdminMenuStates.MAIN_MENU)
        )
        dp.message.register(
            self.handle_back,
            lambda msg: msg.text == "🔙 Назад",
            StateFilter(AdminMenuStates.SURVEYS_MENU, AdminMenuStates.ANALYTICS_MENU, AdminMenuStates.SETTINGS_MENU)
        )
        dp.message.register(
            self.handle_surveys_menu,
            lambda msg: msg.text in [
                "Создать опрос",
                "Мои опросы",
                "Шаблоны вопросов",
                "Настройки опросов",
            ],
            StateFilter(AdminMenuStates.SURVEYS_MENU),
        )
        dp.message.register(
            self.handle_analytics_menu,
            lambda msg: msg.text in [
                "Статистика опросов",
                "Экспорт данных",
                "Активность группы",
                "Рейтинги",
            ],
            StateFilter(AdminMenuStates.ANALYTICS_MENU),
        )
        dp.message.register(
            self.handle_settings_menu,
            lambda msg: msg.text in [
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
        return {
            'admin_main': ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton("📊 Опросы"), KeyboardButton("📈 Аналитика")],
                    [KeyboardButton("⚙ Настройки")]
                ],
                resize_keyboard=True,
                one_time_keyboard=False
            ),
            'admin_surveys': ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton("Создать опрос"), KeyboardButton("Мои опросы")],
                    [KeyboardButton("Шаблоны вопросов"), KeyboardButton("Настройки опросов")],
                    [KeyboardButton("🔙 Назад")]
                ],
                resize_keyboard=True,
                one_time_keyboard=False
            ),
            'admin_analytics': ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton("Статистика опросов"), KeyboardButton("Экспорт данных")],
                    [KeyboardButton("Активность группы"), KeyboardButton("Рейтинги")],
                    [KeyboardButton("🔙 Назад")]
                ],
                resize_keyboard=True,
                one_time_keyboard=False
            ),
            'admin_settings': ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton("Общие настройки"), KeyboardButton("Настройки уведомлений")],
                    [KeyboardButton("Управление доступом"), KeyboardButton("Тестовый режим")],
                    [KeyboardButton("🔙 Назад")]
                ],
                resize_keyboard=True,
                one_time_keyboard=False
            )
        }
    
    async def cmd_admin_menu(self, message: types.Message, state: FSMContext):
        """Обрабатывает команду /admin"""
        logger.debug(f"{message.text} from {message.from_user.id}")
        if message.from_user.id not in self.admin_ids:
            await message.answer("У вас нет доступа к меню администратора.")
            return
        await state.set_state(AdminMenuStates.MAIN_MENU)
        await message.answer("Главное меню администратора:", reply_markup=self.get_keyboards()['admin_main'])
    
    async def handle_main_menu(self, message: types.Message, state: FSMContext):
        """Обрабатывает выбор пункта главного меню"""
        if message.text == "📊 Опросы":
            await state.set_state(AdminMenuStates.SURVEYS_MENU)
            await message.answer("Меню управления опросами:", reply_markup=self.get_keyboards()['admin_surveys'])
        elif message.text == "📈 Аналитика":
            await state.set_state(AdminMenuStates.ANALYTICS_MENU)
            await message.answer("Меню аналитики:", reply_markup=self.get_keyboards()['admin_analytics'])
        elif message.text == "⚙ Настройки":
            await state.set_state(AdminMenuStates.SETTINGS_MENU)
            await message.answer("Меню настроек:", reply_markup=self.get_keyboards()['admin_settings'])

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
        await message.answer("Главное меню администратора:", reply_markup=self.get_keyboards()['admin_main'])

def load_plugin():
    """Загружает плагин"""
    return AdminMenuPlugin()
