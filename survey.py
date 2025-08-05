import logging
from aiogram import Router, Bot, F, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db_manager import get_questions_by_survey, get_survey_name_by_id, get_group_info_by_chat_id
from data_manager import save_to_excel as dm_save_to_excel
from group_event import unrestrict_user_if_needed
from datetime import datetime

router = Router()

class SurveyState(StatesGroup):
    answering = State()

@router.message(CommandStart())
async def start_survey(message: Message, state: FSMContext):
    args = message.text.split()
    user_id = message.from_user.id
    logging.info(f"User {user_id} started survey with args: {args}")

    if len(args) > 1 and args[1].startswith('survey_'):
        parts = args[1].split('_', 2)
        if len(parts) < 3:
            await message.answer("Некорректный формат ссылки. Пожалуйста, попробуйте еще раз.", parse_mode='HTML')
            logging.warning(f"User {user_id} provided invalid survey args: {args}")
            return
        survey_id_str = parts[1]
        chat_id_str = parts[2]
        try:
            survey_id = int(survey_id_str)
            chat_id = int(chat_id_str)
        except ValueError:
            await message.answer("Некорректные идентификаторы опроса или чата.", parse_mode='HTML')
            logging.warning(f"User {user_id} provided invalid survey_id or chat_id: {args}")
            return
    else:
        await message.answer("Опрос не найден. Пожалуйста, попробуйте еще раз.", parse_mode='HTML')
        logging.warning(f"User {user_id} did not provide survey ID.")
        return

    questions = get_questions_by_survey(survey_id)
    survey_name = get_survey_name_by_id(survey_id)
    if not questions:
        await message.answer("Опрос не найден или не содержит вопросов.", parse_mode='HTML')
        logging.warning(f"Survey ID {survey_id} not found or has no questions.")
        return

    # Получаем информацию о группе по chat_id
    group_info = get_group_info_by_chat_id(chat_id)
    if not group_info:
        await message.answer("Информация о группе не найдена.", parse_mode='HTML')
        logging.warning(f"Group info not found for chat_id {chat_id}")
        return
    group_id, group_name = group_info

    await state.update_data(
        survey_id=survey_id,
        survey_name=survey_name,
        questions=questions,
        current_question=0,
        responses=[],
        group_id=group_id,
        group_name=group_name,
        survey_date=datetime.now().strftime("%d-%m-%Y")  # Изменен формат даты
    )
    logging.info(f"Survey session started for user {user_id} with survey '{survey_name}' (ID: {survey_id}) in group '{group_name}' (ID: {group_id})")
    await ask_next_question(message, state)

async def ask_next_question(message: Message, state: FSMContext):
    data_state = await state.get_data()
    current_question_index = data_state['current_question']
    questions = data_state['questions']

    if current_question_index < len(questions):
        question = questions[current_question_index]
        await message.answer(question, parse_mode='HTML')
        await state.set_state(SurveyState.answering)
    else:
        await save_survey_results(message, state)

@router.message(SurveyState.answering)
async def handle_survey_response(message: Message, state: FSMContext):
    data_state = await state.get_data()
    responses = data_state.get('responses', [])
    responses.append(message.text)
    await state.update_data(responses=responses, current_question=data_state['current_question'] + 1)
    await ask_next_question(message, state)

async def save_survey_results(message: Message, state: FSMContext):
    data_state = await state.get_data()
    user_id = message.from_user.id
    survey_name = data_state['survey_name']
    responses = [{'question': q, 'answer': a} for q, a in zip(data_state['questions'], data_state['responses'])]

    # Получение информации о пользователе
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name if message.from_user.last_name else ""
    username = message.from_user.username if message.from_user.username else ""

    # Получение информации о группе
    group_id = data_state.get('group_id')
    group_name = data_state.get('group_name')

    # Получение даты прохождения опроса
    survey_date = data_state.get('survey_date')

    dm_save_to_excel(
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        username=username,
        group_id=group_id,
        group_name=group_name,
        survey_date=survey_date,
        responses=responses,
        survey_name=survey_name
    )
    await message.answer("Спасибо за ваши ответы! Ваши данные сохранены.", parse_mode='HTML')

    # Если капча включена, разблокируем пользователя
    await unrestrict_user_if_needed(message.bot, user_id)

    await state.clear()

def register_survey_handlers(dp: Dispatcher):
    dp.include_router(router)
