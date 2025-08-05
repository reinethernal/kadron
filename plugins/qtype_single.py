from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


class QTypeSingleStates(StatesGroup):
    waiting_answer = State()


class QTypeSinglePlugin:
    __plugin_meta__ = {
        "name": "qtype_single",
        "description": "Demonstrates a single-choice question",
        "version": "1.0.0",
    }

    def __init__(self, bot, plugin_manager):
        self.bot = bot
        self.plugin_manager = plugin_manager
        self.router = Router()

    def register_handlers(self):
        self.router.message(Command("qsingle"))(self.start)
        self.router.callback_query(F.data.startswith("qsingle:"))(self.process_choice)

    def get_commands(self):
        return [
            BotCommand(command="qsingle", description="Single-choice question demo")
        ]

    async def start(self, message: Message, state: FSMContext):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Option A", callback_data="qsingle:A")],
                [InlineKeyboardButton(text="Option B", callback_data="qsingle:B")],
            ]
        )
        await message.answer("Choose one option:", reply_markup=keyboard)
        await state.set_state(QTypeSingleStates.waiting_answer)

    async def process_choice(self, call: CallbackQuery, state: FSMContext):
        choice = call.data.split(":")[1]
        await call.message.edit_text(f"You chose: {choice}")
        await state.clear()


def load_plugin(bot, plugin_manager):
    plugin = QTypeSinglePlugin(bot, plugin_manager)
    plugin.register_handlers()
    return plugin
