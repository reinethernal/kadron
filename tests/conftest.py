import sys, types

# Minimal aiogram stubs for plugin imports
aiogram = types.ModuleType('aiogram')
aiogram.Dispatcher = type('Dispatcher', (), {})
aiogram.Bot = type('Bot', (), {})
class _Handler:
    def __call__(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def register(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

class Router:
    def __init__(self):
        self.message = _Handler()
        self.callback_query = _Handler()
    def include_router(self, *args, **kwargs):
        pass

aiogram.Router = Router

# submodule: types
types_mod = types.ModuleType('aiogram.types')
types_mod.BotCommand = type('BotCommand', (), {})
types_mod.CallbackQuery = type('CallbackQuery', (), {'data': ''})
types_mod.Message = type('Message', (), {})
class ChatPermissions:
    def __init__(self, **kwargs):
        self.permissions = kwargs
types_mod.ChatPermissions = ChatPermissions
def _getattr(name):
    cls = type(name, (), {})
    setattr(types_mod, name, cls)
    return cls
types_mod.__getattr__ = _getattr
aiogram.types = types_mod

# submodule: filters
filters_mod = types.ModuleType('aiogram.filters')
class Command:
    def __init__(self, *args, **kwargs):
        pass
class StateFilter:
    def __init__(self, *args, **kwargs):
        pass
class ChatMemberUpdatedFilter:
    def __init__(self, *args, **kwargs):
        pass
filters_mod.Command = Command
filters_mod.StateFilter = StateFilter
filters_mod.ChatMemberUpdatedFilter = ChatMemberUpdatedFilter
aiogram.filters = filters_mod

# FSM context/state
fsm_mod = types.ModuleType('aiogram.fsm')
context_mod = types.ModuleType('aiogram.fsm.context')
context_mod.FSMContext = type('FSMContext', (), {})
state_mod = types.ModuleType('aiogram.fsm.state')
state_mod.State = type('State', (), {})
state_mod.StatesGroup = type('StatesGroup', (), {})
fsm_mod.context = context_mod
fsm_mod.state = state_mod
aiogram.fsm = fsm_mod

# utils.keyboard
utils_mod = types.ModuleType('aiogram.utils')
keyboard_mod = types.ModuleType('aiogram.utils.keyboard')
class _Builder:
    def button(self, **kwargs):
        pass
    def adjust(self, *args, **kwargs):
        pass
    def as_markup(self):
        return None
keyboard_mod.InlineKeyboardBuilder = _Builder
utils_mod.keyboard = keyboard_mod
aiogram.utils = utils_mod

client_bot_mod = types.ModuleType('aiogram.client.bot')
client_bot_mod.Bot = aiogram.Bot

sys.modules.setdefault('aiogram', aiogram)
sys.modules.setdefault('aiogram.types', types_mod)
sys.modules.setdefault('aiogram.filters', filters_mod)
sys.modules.setdefault('aiogram.fsm', fsm_mod)
sys.modules.setdefault('aiogram.fsm.context', context_mod)
sys.modules.setdefault('aiogram.fsm.state', state_mod)
sys.modules.setdefault('aiogram.utils', utils_mod)
sys.modules.setdefault('aiogram.utils.keyboard', keyboard_mod)
sys.modules.setdefault('aiogram.client.bot', client_bot_mod)

# Stubs for additional libraries
dotenv_mod = types.ModuleType('dotenv')
def load_dotenv(*args, **kwargs):
    pass
dotenv_mod.load_dotenv = load_dotenv
sys.modules.setdefault('dotenv', dotenv_mod)

pandas_mod = types.ModuleType('pandas')
pandas_mod.DataFrame = type('DataFrame', (), {})
sys.modules.setdefault('pandas', pandas_mod)
sys.modules.setdefault('openpyxl', types.ModuleType('openpyxl'))
