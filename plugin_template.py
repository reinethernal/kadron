"""
Шаблон плагина для Telegram‑бота.

Этот файл задаёт основную структуру для создания новых плагинов. Каждый плагин
должен реализовать обязательные методы и зарегистрировать себя в менеджере плагинов.

Использование:
1. Скопируйте этот шаблон;
2. Переименуйте файл в `your_name_plugin.py`;
3. Реализуйте необходимые методы;
4. Плагин будет автоматически загружен менеджером.

Обязательные методы:
- `register_handlers(dp)` — регистрация обработчиков;
- `get_commands()` — список поддерживаемых команд.

Необязательные методы:
- `get_keyboards()` — необходимые клавиатуры;
- `on_plugin_load()` — вызывается при загрузке плагина;
- `on_plugin_unload()` — вызывается при выгрузке плагина.
"""

from aiogram import Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


class PluginStates(StatesGroup):
    """Состояния для примера плагина"""
    SomeState = State()


class PluginTemplate:
    """Шаблонный класс для создания новых плагинов"""
    
    def __init__(self):
        self.name = "template_plugin"
        self.description = "Template Plugin"
        
    async def register_handlers(self, dp: Dispatcher):
        """Регистрация всех обработчиков плагина"""
        dp.message.register(self.command_handler, Command("template_command"))
        # Добавляйте другие обработчики при необходимости
        
    def get_commands(self):
        """Возвращает список команд, предоставляемых плагином"""
        return [
            types.BotCommand("template_command", "Template command")
        ]
        
    def get_keyboards(self):
        """Возвращает клавиатуры, необходимые плагину"""
        return {
            "main": ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton("Template Button")],
                    [KeyboardButton("Another Button")]
                ],
                resize_keyboard=True
            ),
            "inline": InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("Button 1", callback_data="btn1"),
                InlineKeyboardButton("Button 2", callback_data="btn2")
            )
        }
        
    def on_plugin_load(self):
        """Вызывается при загрузке плагина"""
        print(f"Plugin {self.name} loaded")
        
    def on_plugin_unload(self):
        """Вызывается при выгрузке плагина"""
        print(f"Plugin {self.name} unloaded")
        
    async def command_handler(self, message: types.Message, state: FSMContext):
        """Пример обработчика команды"""
        await message.answer("Это пример обработчика команды")


# Эта функция необходима менеджеру плагинов для загрузки плагина
def load_plugin():
    """Загружает плагин"""
    return PluginTemplate()
