"""
Captcha Plugin for Telegram Bot (aiogram 3.x)

Обрабатываем новых участников через ChatMemberUpdated.
Исправлен импорт типов и убрано "state=" из регистрации хендлера,
вместо этого используем фильтр StateFilter(PrimarySurveyStates.AWAITING_RESPONSE).
"""

import asyncio
import logging
import random
import string

from aiogram import Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ChatMemberUpdated, Message, CallbackQuery, ChatPermissions
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import ChatMemberUpdatedFilter, StateFilter
from core.db_manager import add_user_to_pending
from .group_event_plugin import unrestrict_user_if_needed

try:
    from .storage_plugin import storage
except ImportError:
    class DummyStorage:
        def get_user_state(self, user_id): return {}
        def set_user_state(self, user_id, key, value): pass
        def get_setting(self, key, default=None): return default
    storage = DummyStorage()

logger = logging.getLogger(__name__)

class PrimarySurveyStates(StatesGroup):
    """States for primary survey after captcha"""
    AWAITING_RESPONSE = State()

class CaptchaPlugin:
    """Plugin for captcha functionality"""
    
    def __init__(self):
        self.name = "captcha_plugin"
        self.description = "Captcha verification for new members"
        self.pending_captchas = {}
        self.warning_tasks = {}
        
        # Пример вопросов
        self.primary_survey_questions = [
            {
                "id": "name",
                "text": "Как вас зовут? (Имя и фамилия)",
                "type": "text"
            },
            {
                "id": "interests",
                "text": "Какие темы вас интересуют?",
                "type": "multiple_choice",
                "options": ["Технологии", "Бизнес", "Наука", "Искусство", "Спорт", "Другое"]
            },
            {
                "id": "experience",
                "text": "Ваш опыт в данной области?",
                "type": "single_choice",
                "options": ["Новичок", "Средний уровень", "Продвинутый", "Эксперт"]
            }
        ]
    
    async def register_handlers(self, dp: Dispatcher):
        """
        Регистрируем хендлеры для aiogram 3.x
        """
        # 1) Обработка новых участников
        dp.chat_member.register(
            self.on_new_chat_member,
            ChatMemberUpdatedFilter(member_status_changed=['member', 'creator', 'administrator'])
        )
        
        # 2) Обработка капчи
        dp.callback_query.register(
            self.process_captcha,
            lambda c: c.data.startswith("captcha_")
        )
        
        # 3) Ограничиваем пользователей в группах, если капча не пройдена
        dp.message.register(
            self.check_access,
            lambda msg: msg.chat.type in ["group", "supergroup"]
            and not self.is_access_granted(msg.from_user.id)
        )
        
        # 4) Запуск короткого опроса после капчи
        dp.callback_query.register(
            self.start_primary_survey,
            lambda c: c.data == "start_primary_survey"
        )
        dp.callback_query.register(
            self.process_primary_survey_choice,
            lambda c: c.data.startswith("primary_choice_")
        )
        
        # 5) Обработка текстового ответа в состоянии AWAITING_RESPONSE
        dp.message.register(
            self.process_primary_survey_text,
            StateFilter(PrimarySurveyStates.AWAITING_RESPONSE)
        )
    
    def get_commands(self):
        return []
    
    def is_access_granted(self, user_id: int) -> bool:
        """
        Проверяем, прошёл ли пользователь капчу и опрос.
        """
        user_state = storage.get_user_state(user_id)
        return user_state.get('passed_primary_survey', False) or user_state.get('passed_captcha', False)
    
    async def on_new_chat_member(self, event: ChatMemberUpdated):
        """
        Обрабатываем вступление нового участника (ChatMemberUpdated).
        """
        user = event.from_user
        if user.is_bot:
            return

        chat_id = event.chat.id
        # Ограничиваем права нового пользователя
        try:
            await event.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False
                )
            )
        except Exception as e:
            logger.error(f"Не удалось ограничить пользователя {user.id}: {e}")

        # Добавляем в список ожидающих прохождения капчи
        add_user_to_pending(user.id, chat_id)

        # Генерация капчи
        captcha_text = self._generate_captcha()
        self.pending_captchas[user.id] = captcha_text
        
        # Кнопки
        builder = InlineKeyboardBuilder()
        options = [captcha_text] + [self._generate_captcha() for _ in range(5)]
        random.shuffle(options)
        for option in options:
            builder.button(
                text=option,
                callback_data=f"captcha_{user.id}_{option}"
            )
        builder.adjust(3)
        markup = builder.as_markup()

        await event.bot.send_message(
            chat_id,
            f"Привет, {user.first_name}! Пожалуйста, пройдите капчу.\nВыберите: {captcha_text}",
            reply_markup=markup
        )

        # Задача предупреждения
        self.warning_tasks[user.id] = asyncio.create_task(
            self._schedule_warning(chat_id, user.id, event.bot)
        )

    async def process_captcha(self, callback_query: CallbackQuery):
        parts = callback_query.data.split('_')
        user_id = int(parts[1])
        selected_option = parts[2]
        
        if callback_query.from_user.id != user_id:
            await callback_query.answer("Это не ваша капча!")
            return
        
        correct_option = self.pending_captchas.get(user_id)
        if not correct_option:
            await callback_query.answer("Капча устарела или уже решена.")
            return
        
        if selected_option == correct_option:
            storage.set_user_state(user_id, 'passed_captcha', True)
            del self.pending_captchas[user_id]
            
            if user_id in self.warning_tasks:
                self.warning_tasks[user_id].cancel()
                del self.warning_tasks[user_id]
            
            # Предлагаем пройти опрос
            builder = InlineKeyboardBuilder()
            builder.button(text="Пройти короткий опрос", callback_data="start_primary_survey")
            markup = builder.as_markup()
            await callback_query.message.edit_text(
                "✅ Капча успешно пройдена!\n\n"
                "Пройдите короткий опрос, чтобы мы могли лучше узнать вас:",
                reply_markup=markup
            )
            await callback_query.answer()
        else:
            await callback_query.answer("Неверно, попробуйте ещё раз!")
    
    async def check_access(self, message: Message):
        """Предотвращаем отправку сообщений без прохождения капчи."""
        if message.chat.type == "private":
            return

        user_id = message.from_user.id

        # Пытаемся повторно ограничить пользователя, если это не сделано
        try:
            await message.bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
            )
        except Exception as e:
            logger.error(f"Не удалось ограничить пользователя {user_id}: {e}")

        if user_id in self.pending_captchas:
            builder = InlineKeyboardBuilder()
            builder.button(
                text="Пройти капчу",
                url=f"https://t.me/{message.bot.username}?start=captcha"
            )
            markup = builder.as_markup()
            try:
                await message.answer(
                    "❌ Вы не можете писать, пока не пройдёте капчу!",
                    reply_markup=markup,
                )
            except Exception as e:
                logger.error(f"Ошибка отправки напоминания: {e}")
    
    async def _schedule_warning(self, chat_id: int, user_id: int, bot):
        """4 минуты ждём, потом предупреждаем, ещё минуту ждём — кик."""
        try:
            await asyncio.sleep(240)
            if user_id in self.pending_captchas:
                builder = InlineKeyboardBuilder()
                builder.button(
                    text="Пройти капчу сейчас",
                    url=f"https://t.me/{bot.username}?start=captcha"
                )
                markup = builder.as_markup()
                await bot.send_message(
                    chat_id,
                    f"⚠️ <a href='tg://user?id={user_id}'>Пользователь</a>, 1 минута на капчу!",
                    reply_markup=markup,
                    parse_mode="HTML"
                )
                await asyncio.sleep(60)
                if user_id in self.pending_captchas:
                    admin_ids = storage.get_setting('admin_ids', [])
                    for admin_id in admin_ids:
                        try:
                            await bot.send_message(
                                admin_id,
                                f"🔴 Пользователь {user_id} будет удалён (не прошёл капчу)"
                            )
                        except Exception as e:
                            logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
                    try:
                        await bot.kick_chat_member(chat_id, user_id)
                        await bot.unban_chat_member(chat_id, user_id)
                    except Exception as e:
                        logger.error(f"Ошибка кика: {e}")
                    del self.pending_captchas[user_id]
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Ошибка в задаче предупреждения: {e}")
    
    def _generate_captcha(self) -> str:
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    
    async def start_primary_survey(self, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        storage.set_user_state(user_id, 'primary_survey_index', 0)
        await self.show_primary_survey_question(callback_query.message, user_id, 0)
        await callback_query.answer()
    
    async def show_primary_survey_question(self, message: Message, user_id: int, question_index: int):
        if question_index >= len(self.primary_survey_questions):
            storage.set_user_state(user_id, 'passed_primary_survey', True)
            await message.edit_text("✅ Спасибо за заполнение опроса! Теперь у вас полный доступ.")
            await unrestrict_user_if_needed(message.bot, user_id)
            return
        
        question = self.primary_survey_questions[question_index]
        
        if question['type'] == 'text':
            builder = InlineKeyboardBuilder()
            builder.button(
                text="Ответить",
                callback_data=f"primary_text_{question['id']}"
            )
            markup = builder.as_markup()
            await message.edit_text(
                f"{question['text']}\n\nНажмите кнопку, чтобы ответить:",
                reply_markup=markup
            )
        
        elif question['type'] == 'single_choice':
            builder = InlineKeyboardBuilder()
            for i, option in enumerate(question['options']):
                builder.button(
                    text=option,
                    callback_data=f"primary_choice_{question['id']}_{i}"
                )
            builder.adjust(1)
            markup = builder.as_markup()
            await message.edit_text(
                f"{question['text']}\n\nВыберите один вариант:",
                reply_markup=markup
            )
        
        elif question['type'] == 'multiple_choice':
            builder = InlineKeyboardBuilder()
            for i, option in enumerate(question['options']):
                builder.button(
                    text=option,
                    callback_data=f"primary_choice_{question['id']}_{i}"
                )
            builder.button(
                text="Подтвердить",
                callback_data=f"primary_submit_{question['id']}"
            )
            builder.adjust(1)
            markup = builder.as_markup()
            await message.edit_text(
                f"{question['text']}\n\nВыберите несколько вариантов:",
                reply_markup=markup
            )

    async def process_primary_survey_choice(self, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        parts = callback_query.data.split('_')
        if len(parts) < 3:
            await callback_query.answer("Неверный формат данных")
            return
        
        question_id = parts[2]
        
        if parts[0] == 'primary' and parts[1] == 'text':
            # Переходим к текстовому ответу
            await callback_query.message.edit_text(
                f"Введите ваш ответ:\n\n"
                f"{next((q['text'] for q in self.primary_survey_questions if q['id'] == question_id), '')}"
            )
            # вместо state=..., в 3.x используем get_current().current_state(...)
            state = Dispatcher.get_current().current_state(user=user_id, chat=callback_query.message.chat.id)
            await state.update_data(question_id=question_id)
            # Здесь просто ставим состояние, но при регистрации мы опираемся не на state=..., а на фильтр
            await state.set_state(PrimarySurveyStates.AWAITING_RESPONSE)
        
        elif parts[0] == 'primary' and parts[1] == 'choice' and len(parts) > 3:
            option_index = int(parts[3])
            question = next((q for q in self.primary_survey_questions if q['id'] == question_id), None)
            if not question:
                await callback_query.answer("Вопрос не найден.")
                return
            
            if question['type'] == 'single_choice':
                storage.set_user_state(user_id, f'primary_answer_{question_id}', option_index)
                current_index = storage.get_user_state(user_id).get('primary_survey_index', 0)
                next_index = current_index + 1
                storage.set_user_state(user_id, 'primary_survey_index', next_index)
                await self.show_primary_survey_question(callback_query.message, user_id, next_index)
            
            elif question['type'] == 'multiple_choice':
                selections_key = f'primary_answer_{question_id}'
                selections = storage.get_user_state(user_id).get(selections_key, [])
                if option_index in selections:
                    selections.remove(option_index)
                else:
                    selections.append(option_index)
                storage.set_user_state(user_id, selections_key, selections)
                
                # Обновляем варианты
                builder = InlineKeyboardBuilder()
                for i, option in enumerate(question['options']):
                    text = f"✅ {option}" if i in selections else option
                    builder.button(
                        text=text,
                        callback_data=f"primary_choice_{question_id}_{i}"
                    )
                builder.button(
                    text="Подтвердить",
                    callback_data=f"primary_submit_{question_id}"
                )
                builder.adjust(1)
                markup = builder.as_markup()
                await callback_query.message.edit_reply_markup(reply_markup=markup)
        
        elif parts[0] == 'primary' and parts[1] == 'submit':
            current_index = storage.get_user_state(user_id).get('primary_survey_index', 0)
            next_index = current_index + 1
            storage.set_user_state(user_id, 'primary_survey_index', next_index)
            await self.show_primary_survey_question(callback_query.message, user_id, next_index)
        
        await callback_query.answer()
    
    async def process_primary_survey_text(self, message: Message, state: FSMContext):
        data = await state.get_data()
        question_id = data.get('question_id')
        if not question_id:
            await message.reply("Ошибка. Начните заново.")
            await state.clear()
            return
        
        user_id = message.from_user.id
        storage.set_user_state(user_id, f'primary_answer_{question_id}', message.text)
        
        current_index = storage.get_user_state(user_id).get('primary_survey_index', 0)
        next_index = current_index + 1
        storage.set_user_state(user_id, 'primary_survey_index', next_index)
        
        await state.clear()
        
        confirmation = await message.reply("✅ Ваш ответ записан!")
        await self.show_primary_survey_question(confirmation, user_id, next_index)
    
    def on_plugin_load(self):
        logger.info("Плагин капчи загружен")
    
    def on_plugin_unload(self):
        for task in self.warning_tasks.values():
            task.cancel()
        logger.info("Плагин капчи выгружен")

def load_plugin():
    return CaptchaPlugin()
