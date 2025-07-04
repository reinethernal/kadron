# handlers/survey_handlers.py

import logging
from datetime import datetime
from aiogram import Router, Bot, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from core.db_manager import get_poll_by_id, get_welcome_message, update_user_activity
from plugins.survey_plugin import get_questions
from utils.data_manager import save_to_excel

router = Router()
logger = logging.getLogger(__name__)

async def send_question(user_id: int, bot: Bot, state: FSMContext):
    data = await state.get_data()
    poll_id = data.get('poll_id')
    current_index = data.get('current_question_index', 0)
    responses = data.get('responses', [])
    questions = get_questions(poll_id)
    if current_index >= len(questions):
        await bot.send_message(user_id, "Спасибо за участие в опросе!")
        # Сохраняем результаты в Excel (результаты не записываются в БД)
        first_name = data.get('first_name', "")
        last_name = data.get('last_name', "")
        username = data.get('username', "")
        group_id = "private"  # для личного чата
        group_name = "private"
        poll_date = datetime.now().strftime("%d.%m.%Y %H:%M")
        poll_details = get_poll_by_id(poll_id)
        poll_name = poll_details.get("name", f"poll_{poll_id}")
        save_to_excel(user_id, first_name, last_name, username, group_id, group_name, poll_date, responses, poll_name)
        await state.clear()
        return

    question = questions[current_index]
    # Сохраняем текущий текст вопроса (для текстовых ответов)
    await state.update_data(current_question_text=question['text'])
    question_text = question['text']
    q_type = question['type']
    options = question['options']

    if q_type == "Одиночный выбор":
        buttons = []
        for idx, option in enumerate(options):
            buttons.append([InlineKeyboardButton(text=option, callback_data=f"answer_{current_index}_{idx}")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    elif q_type == "Множественный выбор":
        selected = data.get('selected_options', {}).get(str(current_index), [])
        buttons = []
        for idx, option in enumerate(options):
            btn_text = f"✅ {option}" if idx in selected else option
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"toggle_{current_index}_{idx}")])
        buttons.append([InlineKeyboardButton(text="Подтвердить", callback_data=f"confirm_{current_index}")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    else:
        # Текстовый ответ
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отправить ответ", callback_data=f"send_text_{current_index}")]
        ])

    await bot.send_message(user_id, question_text, reply_markup=keyboard)
    logger.info(f"Отправлен вопрос {current_index + 1} пользователю {user_id}.")

@router.message(Command("start"))
async def start_handler(message: types.Message, bot: Bot, state: FSMContext):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    username = message.from_user.username or ""
    update_user_activity(user_id, username)
    await state.update_data(first_name=first_name, last_name=last_name, username=username)
    
    # Извлекаем аргументы команды вручную из message.text
    text = message.text or ""
    parts = text.split(maxsplit=1)
    args = parts[1] if len(parts) > 1 else ""
    
    if args and args.startswith("survey_"):
        try:
            poll_id = int(args.split("_")[1])
        except (ValueError, IndexError):
            await message.answer("Неверная ссылка опроса.")
            return
        questions = get_questions(poll_id)
        if not questions:
            await message.answer("В этом опросе нет вопросов.")
            return
        await state.update_data(poll_id=poll_id, current_question_index=0, responses=[], selected_options={})
        await send_question(user_id, bot, state)
        return

    welcome_message = get_welcome_message()
    if welcome_message:
        welcome_text = welcome_message.replace("{username}", message.from_user.full_name)
    else:
        welcome_text = "Добро пожаловать! Используйте /admin для доступа к административным функциям."
    await message.answer(welcome_text)

@router.callback_query(lambda c: c.data and c.data.startswith("answer_"))
async def answer_callback_handler(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = callback_query.data.split("_")
    if len(data) != 3:
        await bot.send_message(callback_query.from_user.id, "Неверный формат ответа.")
        return
    _, q_index_str, opt_index_str = data
    try:
        q_index = int(q_index_str)
        opt_index = int(opt_index_str)
    except ValueError:
        await bot.send_message(callback_query.from_user.id, "Неверный формат ответа.")
        return

    current_data = await state.get_data()
    poll_id = current_data.get('poll_id')
    questions = get_questions(poll_id)
    if q_index >= len(questions):
        await bot.send_message(callback_query.from_user.id, "Вопрос не найден.")
        return

    question = questions[q_index]
    try:
        option = question['options'][opt_index]
    except IndexError:
        await bot.send_message(callback_query.from_user.id, "Выбран неверный вариант.")
        return

    responses = current_data.get('responses', [])
    responses.append({"question": question['text'], "answer": option})
    await state.update_data(responses=responses, current_question_index=q_index + 1)
    await bot.send_message(callback_query.from_user.id, f"Вы выбрали: {option}")
    await send_question(callback_query.from_user.id, bot, state)

@router.callback_query(lambda c: c.data and c.data.startswith("toggle_"))
async def toggle_option_handler(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = callback_query.data.split("_")
    if len(data) != 3:
        await bot.send_message(callback_query.from_user.id, "Неверный формат ответа.")
        return
    _, q_index_str, opt_index_str = data
    try:
        q_index = int(q_index_str)
        opt_index = int(opt_index_str)
    except ValueError:
        await bot.send_message(callback_query.from_user.id, "Неверный формат ответа.")
        return

    current_data = await state.get_data()
    selected_options = current_data.get('selected_options', {})
    key = str(q_index)
    current_selection = selected_options.get(key, [])
    if opt_index in current_selection:
        current_selection.remove(opt_index)
    else:
        current_selection.append(opt_index)
    selected_options[key] = current_selection
    await state.update_data(selected_options=selected_options)
    poll_id = current_data.get('poll_id')
    questions = get_questions(poll_id)
    if q_index >= len(questions):
        return
    question = questions[q_index]
    buttons = []
    for idx, option in enumerate(question['options']):
        btn_text = f"✅ {option}" if idx in current_selection else option
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"toggle_{q_index}_{idx}")])
    buttons.append([InlineKeyboardButton(text="Подтвердить", callback_data=f"confirm_{q_index}")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.edit_message_reply_markup(callback_query.message.chat.id, callback_query.message.message_id, reply_markup=keyboard)
    await callback_query.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("confirm_"))
async def confirm_multiple_handler(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = callback_query.data.split("_")
    if len(data) != 2:
        await bot.send_message(callback_query.from_user.id, "Неверный формат ответа.")
        return
    try:
        q_index = int(data[1])
    except ValueError:
        await bot.send_message(callback_query.from_user.id, "Неверный формат ответа.")
        return
    current_data = await state.get_data()
    selected_options = current_data.get('selected_options', {}).get(str(q_index), [])
    poll_id = current_data.get('poll_id')
    questions = get_questions(poll_id)
    if q_index >= len(questions):
        await bot.send_message(callback_query.from_user.id, "Вопрос не найден.")
        return
    question = questions[q_index]
    chosen = [question['options'][i] for i in selected_options if i < len(question['options'])]
    answer_text = ", ".join(chosen)
    responses = current_data.get('responses', [])
    responses.append({"question": question['text'], "answer": answer_text})
    await state.update_data(responses=responses, current_question_index=q_index + 1)
    selected_options_all = current_data.get('selected_options', {})
    selected_options_all[str(q_index)] = []
    await state.update_data(selected_options=selected_options_all)
    await bot.send_message(callback_query.from_user.id, f"Ваш выбор: {answer_text}")
    await send_question(callback_query.from_user.id, bot, state)

@router.callback_query(lambda c: c.data and c.data.startswith("send_text_"))
async def send_text_answer_handler(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = callback_query.data.split("_")
    if len(data) != 3:
        await bot.send_message(callback_query.from_user.id, "Неверный формат ответа.")
        return
    _, action, q_index_str = data
    try:
        q_index = int(q_index_str)
    except ValueError:
        await bot.send_message(callback_query.from_user.id, "Неверный формат ответа.")
        return
    await bot.send_message(callback_query.from_user.id, "Введите ваш ответ:")
    await state.update_data(current_question_index=q_index + 1)
    await state.set_state("awaiting_text_answer")

@router.message(StateFilter("awaiting_text_answer"))
async def handle_text_answer(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    answer = message.text.strip()
    data = await state.get_data()
    current_question_text = data.get('current_question_text', "Неизвестный вопрос")
    responses = data.get('responses', [])
    responses.append({"question": current_question_text, "answer": answer})
    await state.update_data(responses=responses)
    await send_question(user_id, bot, state)

def register_survey_handlers(dp: Bot):
    dp.include_router(router)
