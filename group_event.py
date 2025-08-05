import os
import logging
import asyncio
from aiogram import Router, Bot, F, Dispatcher
from aiogram.types import Message, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from db_manager import (
    get_survey_id_by_name,
    add_user_to_pending,
    is_user_pending,
    remove_user_from_pending,
    get_pending_chats_for_user,
    add_group
)
from dotenv import load_dotenv

load_dotenv()
ENABLE_CAPTCHA = os.getenv('ENABLE_CAPTCHA', 'False').lower() == 'true'
CAPTCHA_TIMEOUT = int(os.getenv('CAPTCHA_TIMEOUT', '5'))  # В минутах

router = Router()

@router.message(F.new_chat_members)
async def welcome_new_member(message: Message, bot: Bot):
    if message.new_chat_members:
        # Добавляем группу в базу данных, если ее там нет
        add_group(message.chat.id, message.chat.title)
        for new_member in message.new_chat_members:
            user = new_member
            chat_id = message.chat.id
            survey_id = get_survey_id_by_name("первичный")
            if not survey_id:
                await bot.send_message(chat_id, "Опрос 'первичный' не найден.", parse_mode='HTML')
                return
            survey_param = f"survey_{survey_id}_{chat_id}"  # Добавлено chat_id в параметр

            # Получаем имя пользователя бота
            bot_user = await bot.get_me()
            bot_username = bot_user.username

            deep_link = f"https://t.me/{bot_username}?start={survey_param}"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Пройти анкетирование", url=deep_link)]
                ]
            )
            await bot.send_message(
                chat_id,
                f"Приветствуем, {user.full_name}! Нажмите на кнопку ниже, чтобы пройти анкетирование.",
                reply_markup=keyboard,
                parse_mode='HTML'
            )

            if ENABLE_CAPTCHA:
                await restrict_user(bot, chat_id, user.id)
                add_user_to_pending(user.id, chat_id)
                # Запускаем таймер для проверки
                asyncio.create_task(start_captcha_timer(bot, user.id, chat_id))

async def restrict_user(bot: Bot, chat_id: int, user_id: int):
    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        logging.info(f"User {user_id} restricted in chat {chat_id}")
    except TelegramForbiddenError:
        logging.error(f"Bot lacks permission to restrict members in chat {chat_id}")
    except TelegramBadRequest as e:
        logging.error(f"Failed to restrict user {user_id} in chat {chat_id}: {e}")

async def unrestrict_user_if_needed(bot: Bot, user_id: int):
    pending_chats = get_pending_chats_for_user(user_id)
    for chat_id in pending_chats:
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=True)
            )
            logging.info(f"User {user_id} unrestricted in chat {chat_id}")
            remove_user_from_pending(user_id, chat_id)
        except TelegramForbiddenError:
            logging.error(f"Bot lacks permission to unrestrict members in chat {chat_id}")
        except TelegramBadRequest as e:
            logging.error(f"Failed to unrestrict user {user_id} in chat {chat_id}: {e}")

async def start_captcha_timer(bot: Bot, user_id: int, chat_id: int):
    await asyncio.sleep(CAPTCHA_TIMEOUT * 60)
    if is_user_pending(user_id, chat_id):
        try:
            await bot.kick_chat_member(chat_id=chat_id, user_id=user_id)
            logging.info(f"User {user_id} kicked from chat {chat_id} due to captcha timeout")
            remove_user_from_pending(user_id, chat_id)
        except TelegramForbiddenError:
            logging.error(f"Bot lacks permission to kick members in chat {chat_id}")
        except TelegramBadRequest as e:
            logging.error(f"Failed to kick user {user_id} from chat {chat_id}: {e}")

def register_group_handlers(dp: Dispatcher):
    dp.include_router(router)
