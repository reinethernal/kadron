"""
Плагин ролей для Telegram-бота

Этот плагин обеспечивает функциональность контроля доступа на основе ролей.
Он управляет назначением ролей пользователям и проверкой разрешений.
"""

import logging
from aiogram import Dispatcher, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter

# Импортируем модуль хранилища
try:
    from .storage_plugin import storage
except ImportError:
    # Запасной вариант для тестирования
    class DummyStorage:
        def get_user_state(self, user_id): return {}
        def set_user_state(self, user_id, key, value): pass
        def get_setting(self, key, default=None): return default
        def set_setting(self, key, value): pass
    storage = DummyStorage()

logger = logging.getLogger(__name__)

# Определяем роли по умолчанию с разрешениями
DEFAULT_ROLES = {
    'admin': {
        'name': 'Администратор',
        'permissions': ['manage_surveys', 'manage_users', 'manage_roles', 'view_analytics', 'export_data']
    },
    'moderator': {
        'name': 'Модератор',
        'permissions': ['manage_surveys', 'view_analytics']
    },
    'user': {
        'name': 'Пользователь',
        'permissions': ['take_surveys']
    },
    'guest': {
        'name': 'Гость',
        'permissions': []
    }
}

class RoleStates(StatesGroup):
    """Состояния для управления ролями"""
    SELECTING_USER = State()         # Выбор пользователя
    SELECTING_ROLE = State()         # Выбор роли
    CREATING_ROLE = State()          # Создание новой роли
    EDITING_ROLE = State()           # Редактирование роли
    EDITING_PERMISSIONS = State()    # Редактирование разрешений роли

class RolesPlugin:
    """Плагин для управления доступом на основе ролей"""
    
    def __init__(self):
        self.name = "roles_plugin"
        self.description = "Контроль доступа на основе ролей"
    
    async def register_handlers(self, dp: Dispatcher):
        """Регистрирует все обработчики для этого плагина"""
        dp.message.register(
            self.cmd_roles,
            Command(commands=["roles"]),
            lambda msg: self.has_permission(msg.from_user.id, 'manage_roles')
        )
        
        dp.callback_query.register(
            self.handle_roles_action,
            lambda c: c.data.startswith('roles_')
        )
        
        dp.callback_query.register(
            self.handle_user_selection,
            lambda c: c.data.startswith('select_user_'),
            StateFilter(RoleStates.SELECTING_USER)
        )
        
        dp.callback_query.register(
            self.handle_role_selection,
            lambda c: c.data.startswith('select_role_'),
            StateFilter(RoleStates.SELECTING_ROLE)
        )
        
        dp.message.register(
            self.process_role_name,
            StateFilter(RoleStates.CREATING_ROLE)
        )
        
        dp.callback_query.register(
            self.handle_permission_toggle,
            lambda c: c.data.startswith('toggle_perm_'),
            StateFilter(RoleStates.EDITING_PERMISSIONS)
        )
        
        dp.callback_query.register(
            self.handle_save_permissions,
            lambda c: c.data == 'save_permissions',
            StateFilter(RoleStates.EDITING_PERMISSIONS)
        )
    
    def get_commands(self):
        """Возвращает список команд, предоставляемых плагином"""
        return [
            types.BotCommand(command="roles", description="Управление ролями пользователей")
        ]
    
    def has_permission(self, user_id, permission):
        """Проверяет, есть ли у пользователя определённое разрешение"""
        # Получаем роль пользователя
        user_role = self.get_user_role(user_id)
        
        # Получаем конфигурацию ролей
        roles = self.get_roles()
        
        # Проверяем, существует ли роль и есть ли у неё разрешение
        if user_role in roles and permission in roles[user_role].get('permissions', []):
            return True
            
        # Особый случай: администраторы (admin_ids) имеют все разрешения
        admin_ids = storage.get_setting('admin_ids', [])
        if user_id in admin_ids:
            return True
            
        return False
    
    def get_user_role(self, user_id):
        """Получает роль пользователя"""
        # Получаем соответствие ролей пользователям
        user_roles = storage.get_setting('user_roles', {})
        
        # Преобразуем user_id в строку для хранения в JSON
        user_id = str(user_id)
        
        # Возвращаем роль пользователя или 'user' по умолчанию
        return user_roles.get(user_id, 'user')
    
    def set_user_role(self, user_id, role):
        """Устанавливает роль пользователю"""
        # Получаем соответствие ролей пользователям
        user_roles = storage.get_setting('user_roles', {})
        
        # Преобразуем user_id в строку для хранения в JSON
        user_id = str(user_id)
        
        # Устанавливаем роль
        user_roles[user_id] = role
        
        # Сохраняем обратно в хранилище
        storage.set_setting('user_roles', user_roles)
    
    def get_roles(self):
        """Получает конфигурацию всех ролей"""
        # Получаем роли из хранилища или используем значения по умолчанию
        roles = storage.get_setting('roles', None)
        
        if not roles:
            # Инициализируем роли по умолчанию
            roles = DEFAULT_ROLES
            storage.set_setting('roles', roles)
            
        return roles
    
    def save_roles(self, roles):
        """Сохраняет конфигурацию ролей"""
        storage.set_setting('roles', roles)
    
    async def cmd_roles(self, message: types.Message):
        """Обрабатывает команду /roles"""
        logger.debug(f"{message.text} from {message.from_user.id}")
        builder = InlineKeyboardBuilder()
        builder.button(text="👤 Назначить роль пользователю", callback_data="roles_assign")
        builder.button(text="✏️ Редактировать роли", callback_data="roles_edit")
        builder.button(text="➕ Создать новую роль", callback_data="roles_create")
        builder.adjust(1)
        markup = builder.as_markup()
        
        await message.answer(
            "🔑 Управление ролями пользователей\n\n"
            "Выберите действие:",
            reply_markup=markup
        )
    
    async def handle_roles_action(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Обрабатывает действия управления ролями"""
        action = callback_query.data.split('_')[1]
        
        if action == "assign":
            # Показываем список пользователей для назначения ролей
            await self.show_user_list(callback_query.message)
            await state.set_state(RoleStates.SELECTING_USER)
            
        elif action == "edit":
            # Показываем список ролей для редактирования
            await self.show_roles_list(callback_query.message)
            
        elif action == "create":
            # Начинаем создание новой роли
            await callback_query.message.edit_text(
                "Создание новой роли\n\n"
                "Введите название для новой роли:"
            )
            await state.set_state(RoleStates.CREATING_ROLE)
            
        await callback_query.answer()
    
    async def show_user_list(self, message: types.Message):
        """Показывает список пользователей для выбора"""
        # Здесь обычно пользователи получаются из чата
        # Для упрощения используем состояния пользователей
        
        # Получаем всех пользователей, взаимодействовавших с ботом
        all_users = {}
        user_states = storage.data.get('users', {})
        
        for user_id, state in user_states.items():
            # Получаем информацию о пользователе, если доступна
            user_info = state.get('user_info', {})
            name = user_info.get('name', f"Пользователь {user_id}")
            
            all_users[user_id] = name
        
        if not all_users:
            await message.edit_text(
                "Нет доступных пользователей. Пользователи появятся в списке после взаимодействия с ботом."
            )
            return
        
        # Создаём клавиатуру с пользователями
        builder = InlineKeyboardBuilder()

        for user_id, name in all_users.items():
            # Получаем текущую роль
            role = self.get_user_role(user_id)
            roles = self.get_roles()
            role_name = roles.get(role, {}).get('name', role)

            builder.button(
                text=f"{name} - {role_name}",
                callback_data=f"select_user_{user_id}"
            )

        builder.button(
            text="⬅️ Назад",
            callback_data="roles_back"
        )
        builder.adjust(1)
        markup = builder.as_markup()
        
        await message.edit_text(
            "Выберите пользователя для назначения роли:",
            reply_markup=markup
        )
    
    async def show_roles_list(self, message: types.Message):
        """Показывает список ролей для редактирования"""
        roles = self.get_roles()
        
        builder = InlineKeyboardBuilder()

        for role_id, role_data in roles.items():
            builder.button(
                text=f"{role_data.get('name', role_id)}",
                callback_data=f"edit_role_{role_id}"
            )

        builder.button(
            text="⬅️ Назад",
            callback_data="roles_back"
        )
        builder.adjust(1)
        markup = builder.as_markup()
        
        await message.edit_text(
            "Выберите роль для редактирования:",
            reply_markup=markup
        )
    
    async def handle_user_selection(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Обрабатывает выбор пользователя для назначения роли"""
        user_id = callback_query.data.split('_')[2]
        
        # Сохраняем выбранного пользователя в состоянии
        await state.update_data(selected_user_id=user_id)
        
        # Показываем роли для выбора
        roles = self.get_roles()
        
        builder = InlineKeyboardBuilder()

        for role_id, role_data in roles.items():
            builder.button(
                text=role_data.get('name', role_id),
                callback_data=f"select_role_{role_id}"
            )

        builder.button(
            text="⬅️ Назад",
            callback_data="roles_back_to_users"
        )
        builder.adjust(1)
        markup = builder.as_markup()
        
        await callback_query.message.edit_text(
            f"Выберите роль для пользователя {user_id}:",
            reply_markup=markup
        )
        
        await state.set_state(RoleStates.SELECTING_ROLE)
        await callback_query.answer()
    
    async def handle_role_selection(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Обрабатывает выбор роли для назначения"""
        role_id = callback_query.data.split('_')[2]
        
        # Получаем выбранного пользователя из состояния
        state_data = await state.get_data()
        user_id = state_data.get('selected_user_id')
        
        if not user_id:
            await callback_query.answer("Ошибка: пользователь не выбран")
            await state.clear()
            return
        
        # Назначаем роль
        self.set_user_role(user_id, role_id)
        
        # Получаем название роли
        roles = self.get_roles()
        role_name = roles.get(role_id, {}).get('name', role_id)
        
        await callback_query.message.edit_text(
            f"✅ Роль {role_name} успешно назначена пользователю {user_id}."
        )
        
        await state.clear()
        await callback_query.answer()
    
    async def process_role_name(self, message: types.Message, state: FSMContext):
        """Обрабатывает ввод названия новой роли"""
        role_name = message.text.strip()
        
        if not role_name:
            await message.reply("Название роли не может быть пустым. Пожалуйста, введите название:")
            return
        
        # Генерируем идентификатор роли из названия
        role_id = role_name.lower().replace(' ', '_')
        
        # Получаем существующие роли
        roles = self.get_roles()
        
        # Проверяем, существует ли уже такой идентификатор
        if role_id in roles:
            await message.reply(
                f"Роль с идентификатором {role_id} уже существует. Пожалуйста, выберите другое название:"
            )
            return
        
        # Создаём новую роль с пустыми разрешениями
        roles[role_id] = {
            'name': role_name,
            'permissions': []
        }
        
        # Сохраняем роли
        self.save_roles(roles)
        
        # Сохраняем ID роли в состоянии для редактирования разрешений
        await state.update_data(editing_role_id=role_id)
        
        # Показываем интерфейс редактирования разрешений
        await self.show_permissions_editor(message, role_id)
        await state.set_state(RoleStates.EDITING_PERMISSIONS)
    
    async def show_permissions_editor(self, message, role_id):
        """Показывает интерфейс для редактирования разрешений роли"""
        roles = self.get_roles()
        role = roles.get(role_id, {})
        role_permissions = role.get('permissions', [])
        
        # Список всех доступных разрешений
        all_permissions = [
            ('manage_surveys', 'Управление опросами'),
            ('manage_users', 'Управление пользователями'),
            ('manage_roles', 'Управление ролями'),
            ('view_analytics', 'Просмотр аналитики'),
            ('export_data', 'Экспорт данных'),
            ('take_surveys', 'Прохождение опросов')
        ]
        
        builder = InlineKeyboardBuilder()

        for perm_id, perm_name in all_permissions:
            # Проверяем, включено ли разрешение
            status = "✅" if perm_id in role_permissions else "❌"

            builder.button(
                text=f"{status} {perm_name}",
                callback_data=f"toggle_perm_{role_id}_{perm_id}"
            )

        builder.button(
            text="💾 Сохранить",
            callback_data="save_permissions"
        )
        builder.adjust(1)
        markup = builder.as_markup()
        
        await message.reply(
            f"Редактирование разрешений для роли {role.get('name', role_id)}:\n\n"
            f"Нажмите на разрешение, чтобы включить/выключить его:",
            reply_markup=markup
        )
    
    async def handle_permission_toggle(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Обрабатывает переключение разрешения для роли"""
        parts = callback_query.data.split('_')
        role_id = parts[2]
        perm_id = parts[3]
        
        # Получаем роли
        roles = self.get_roles()
        
        if role_id not in roles:
            await callback_query.answer("Роль не найдена")
            return
        
        # Переключаем разрешение
        if 'permissions' not in roles[role_id]:
            roles[role_id]['permissions'] = []
            
        if perm_id in roles[role_id]['permissions']:
            roles[role_id]['permissions'].remove(perm_id)
        else:
            roles[role_id]['permissions'].append(perm_id)
        
        # Сохраняем роли
        self.save_roles(roles)
        
        # Обновляем сообщение с новыми разрешениями
        role_permissions = roles[role_id].get('permissions', [])
        
        # Список всех доступных разрешений
        all_permissions = [
            ('manage_surveys', 'Управление опросами'),
            ('manage_users', 'Управление пользователями'),
            ('manage_roles', 'Управление ролями'),
            ('view_analytics', 'Просмотр аналитики'),
            ('export_data', 'Экспорт данных'),
            ('take_surveys', 'Прохождение опросов')
        ]
        
        builder = InlineKeyboardBuilder()

        for perm_id, perm_name in all_permissions:
            # Проверяем, включено ли разрешение
            status = "✅" if perm_id in role_permissions else "❌"

            builder.button(
                text=f"{status} {perm_name}",
                callback_data=f"toggle_perm_{role_id}_{perm_id}"
            )

        builder.button(
            text="💾 Сохранить",
            callback_data="save_permissions"
        )
        builder.adjust(1)
        markup = builder.as_markup()
        
        await callback_query.message.edit_reply_markup(reply_markup=markup)
        await callback_query.answer()
    
    async def handle_save_permissions(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Обрабатывает сохранение разрешений для роли"""
        await callback_query.message.edit_text(
            "✅ Разрешения роли успешно сохранены."
        )
        
        await state.clear()
        await callback_query.answer()
    
    def on_plugin_load(self):
        """Вызывается при загрузке плагина"""
        logger.info("Плагин ролей загружен")
        
        # Инициализируем роли, если они ещё не существуют
        roles = storage.get_setting('roles', None)
        if not roles:
            storage.set_setting('roles', DEFAULT_ROLES)
    
    def on_plugin_unload(self):
        """Вызывается при выгрузке плагина"""
        logger.info("Плагин ролей выгружен")

def load_plugin():
    """Загружает плагин"""
    return RolesPlugin()
