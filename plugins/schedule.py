from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BotCommand, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message


class SchedulePlugin:
    __plugin_meta__ = {
        "name": "schedule",
        "description": "Shows a simple weekly schedule",
        "version": "1.0.0",
    }

    def __init__(self, bot, plugin_manager):
        self.bot = bot
        self.plugin_manager = plugin_manager
        self.router = Router()
        self.schedule = {
            "Monday": "Math, Physics",
            "Tuesday": "History, Art",
            "Wednesday": "Biology, Chemistry",
            "Thursday": "Sports",
            "Friday": "Computer Science",
        }

    def register_handlers(self):
        self.router.message(Command("schedule"))(self.show_menu)
        self.router.callback_query(F.data.startswith("schedule:"))(self.show_day)

    def get_commands(self):
        return [BotCommand(command="schedule", description="Show weekly schedule")]

    async def show_menu(self, message: Message):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=day, callback_data=f"schedule:{day}")]
                for day in self.schedule.keys()
            ]
        )
        await message.answer("Select a day:", reply_markup=keyboard)

    async def show_day(self, call: CallbackQuery):
        day = call.data.split(":")[1]
        text = self.schedule.get(day, "No schedule available.")
        await call.message.edit_text(f"{day} schedule:\n{text}")


def load_plugin(bot, plugin_manager):
    plugin = SchedulePlugin(bot, plugin_manager)
    plugin.register_handlers()
    return plugin
