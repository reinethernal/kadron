from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BotCommand, Message


class AnonymousStates(StatesGroup):
    waiting_message = State()


class AnonymousPlugin:
    __plugin_meta__ = {
        "name": "anonymous",
        "description": "Send messages anonymously via the bot",
        "version": "1.0.0",
    }

    def __init__(self, bot, plugin_manager):
        self.bot = bot
        self.plugin_manager = plugin_manager
        self.router = Router()

    def register_handlers(self):
        self.router.message(Command("anonymous"))(self.start)
        self.router.message(AnonymousStates.waiting_message)(self.forward_message)

    def get_commands(self):
        return [BotCommand(command="anonymous", description="Send an anonymous message")]

    async def start(self, message: Message, state: FSMContext):
        await message.answer("Send me a message and I will post it anonymously.")
        await state.set_state(AnonymousStates.waiting_message)

    async def forward_message(self, message: Message, state: FSMContext):
        await self.bot.send_message(chat_id=message.chat.id, text=f"Anonymous message: {message.text}")
        await message.delete()
        await state.clear()


def load_plugin(bot, plugin_manager):
    plugin = AnonymousPlugin(bot, plugin_manager)
    plugin.register_handlers()
    return plugin
