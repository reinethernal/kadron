"""
Плагин административного меню для Telegram-бота.

Обеспечивает функциональность меню администратора с поддержкой состояний.
"""

import logging
import os
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
        # Загружаем admin_ids из .env как список целых чисел
        admin_ids_str = os.getenv("ADMIN_IDS", "123456789")  # Значение по умолчанию, если .env не найден
        self.admin_ids = [int(id.strip()) for id in admin_ids_str.split(",")]
    
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
        if message.from_user.id not in self.admin_ids:
            await message.answer("У вас нет доступа к меню администратора.")
            return
        await AdminMenuStates.MAIN_MENU.set()
        await message.answer("Главное меню администратора:", reply_markup=self.get_keyboards()['admin_main'])
    
    async def handle_main_menu(self, message: types.Message, state: FSMContext):
        """Обрабатывает выбор пункта главного меню"""
        if message.text == "📊 Опросы":
            await AdminMenuStates.SURVEYS_MENU.set()
            await message.answer("Меню управления опросами:", reply_markup=self.get_keyboards()['admin_surveys'])
        elif message.text == "📈 Аналитика":
            await AdminMenuStates.ANALYTICS_MENU.set()
            await message.answer("Меню аналитики:", reply_markup=self.get_keyboards()['admin_analytics'])
        elif message.text == "⚙ Настройки":
            await AdminMenuStates.SETTINGS_MENU.set()
            await message.answer("Меню настроек:", reply_markup=self.get_keyboards()['admin_settings'])
    
    async def handle_back(self, message: types.Message, state: FSMContext):
        """Обрабатывает кнопку 'Назад'"""
        await AdminMenuStates.MAIN_MENU.set()
        await message.answer("Главное меню администратора:", reply_markup=self.get_keyboards()['admin_main'])

def load_plugin():
    """Загружает плагин"""
    return AdminMenuPlugin()