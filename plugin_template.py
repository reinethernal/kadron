"""
Plugin Template for Telegram Bot

This template provides the basic structure for creating new plugins for the bot.
Each plugin should implement the required methods and register itself with the plugin manager.

Usage:
1. Copy this template
2. Rename it to your_plugin_name_plugin.py
3. Implement the required methods
4. The plugin will be automatically loaded by the plugin manager

Required methods:
- register_handlers(dp): Register all handlers for this plugin
- get_commands(): Return a list of commands this plugin provides

Optional methods:
- get_keyboards(): Return any keyboards this plugin needs
- on_plugin_load(): Called when the plugin is loaded
- on_plugin_unload(): Called when the plugin is unloaded
"""

from aiogram import Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


class PluginStates(StatesGroup):
    """States for the plugin"""
    SomeState = State()


class PluginTemplate:
    """Template for creating new plugins"""
    
    def __init__(self):
        self.name = "template_plugin"
        self.description = "Template Plugin"
        
    async def register_handlers(self, dp: Dispatcher):
        """Register all handlers for this plugin"""
        dp.message.register(self.command_handler, Command("template_command"))
        # Register more handlers as needed
        
    def get_commands(self):
        """Return a list of commands this plugin provides"""
        return [
            types.BotCommand("template_command", "Template command")
        ]
        
    def get_keyboards(self):
        """Return any keyboards this plugin needs"""
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
        """Called when the plugin is loaded"""
        print(f"Plugin {self.name} loaded")
        
    def on_plugin_unload(self):
        """Called when the plugin is unloaded"""
        print(f"Plugin {self.name} unloaded")
        
    async def command_handler(self, message: types.Message, state: FSMContext):
        """Example command handler"""
        await message.answer("This is a template command handler")


# This function is required for the plugin manager to load the plugin
def load_plugin():
    """Load the plugin"""
    return PluginTemplate()
