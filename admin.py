import os
import logging
from aiogram import Router, Bot, F, Dispatcher
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from db_manager import (
    add_survey,
    survey_exists,
    add_question,
    get_all_surveys,
    get_survey_id_by_name,
    get_survey_name_by_id,
    delete_survey_by_id,
    get_all_groups,
    update_survey_name,
    get_questions_by_survey,
    update_question_text,
    delete_question_by_id,
    add_question_to_survey,
)
from dotenv import load_dotenv

load_dotenv()
ADMIN_IDS = [int(admin_id) for admin_id in os.getenv('ADMIN_IDS').split(',')]

class SurveyCreation(StatesGroup):
    waiting_for_survey_name = State()
    waiting_for_questions = State()

class SendResultsState(StatesGroup):
    waiting_for_survey_selection = State()

class SurveyEdit(StatesGroup):
    choosing_survey = State()
    choosing_edit_action = State()
    renaming_survey = State()
    choosing_question_to_edit = State()
    editing_question = State()
    adding_question = State()
    deleting_question = State()

def is_admin(user_id):
    return user_id in ADMIN_IDS

router = Router()

@router.message(Command('admin'), F.chat.type == "private")
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав доступа к административным функциям.", parse_mode='HTML')
        return

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Создать опрос", callback_data="create_survey")
    keyboard.button(text="Редактировать опрос", callback_data="edit_survey")
    keyboard.button(text="Просмотреть список опросов", callback_data="view_surveys")
    keyboard.button(text="Удалить опрос", callback_data="delete_survey")
    keyboard.button(text="Отправить результаты", callback_data="send_results")
    keyboard.button(text="Повторно отправить опрос", callback_data="resend_survey")
    keyboard.adjust(1)

    # Отправляем начальное сообщение и сохраняем его message_id в состоянии
    sent_message = await message.answer("Выберите действие:", reply_markup=keyboard.as_markup(), parse_mode='HTML')
    await state.update_data(menu_message_id=sent_message.message_id)

@router.callback_query()
async def admin_callback_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(call.from_user.id):
        await call.answer("У вас нет прав доступа.", show_alert=True)
        return

    data = call.data
    data_state = await state.get_data()
    menu_message_id = data_state.get('menu_message_id')

    if data == "create_survey":
        await call.message.edit_text("Введите название опроса.", parse_mode='HTML')
        await state.set_state(SurveyCreation.waiting_for_survey_name)
    elif data == "edit_survey":
        surveys = get_all_surveys()
        if not surveys:
            await call.message.edit_text("Опросы не найдены.", parse_mode='HTML')
            return
        keyboard = InlineKeyboardBuilder()
        for survey in surveys:
            survey_id = get_survey_id_by_name(survey)
            keyboard.button(text=survey, callback_data=f"edit_{survey_id}")
        keyboard.adjust(1)
        await call.message.edit_text("Выберите опрос для редактирования:", reply_markup=keyboard.as_markup(), parse_mode='HTML')
        await state.set_state(SurveyEdit.choosing_survey)
    elif data.startswith("edit_") and data.replace("edit_", "").isdigit():
        survey_id = int(data.replace("edit_", ""))
        survey_name = get_survey_name_by_id(survey_id)
        await state.update_data(survey_id=survey_id, survey_name=survey_name)
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Переименовать опрос", callback_data="rename_survey")
        keyboard.button(text="Редактировать вопросы", callback_data="edit_questions")
        keyboard.adjust(1)
        await call.message.edit_text(f"Вы выбрали опрос '{survey_name}'. Что вы хотите сделать?", reply_markup=keyboard.as_markup(), parse_mode='HTML')
        await state.set_state(SurveyEdit.choosing_edit_action)
    elif data == "rename_survey":
        await call.message.edit_text("Введите новое название опроса.", parse_mode='HTML')
        await state.set_state(SurveyEdit.renaming_survey)
    elif data == "edit_questions":
        data_state = await state.get_data()
        survey_id = data_state.get('survey_id')
        questions = get_questions_by_survey(survey_id, include_ids=True)
        if not questions:
            await call.message.edit_text("В этом опросе нет вопросов.", parse_mode='HTML')
        else:
            keyboard = InlineKeyboardBuilder()
            for question_id, question_text in questions:
                keyboard.button(text=question_text, callback_data=f"edit_question_{question_id}")
            keyboard.adjust(1)
            await call.message.edit_text("Выберите вопрос для редактирования или удаления:", reply_markup=keyboard.as_markup(), parse_mode='HTML')
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Добавить новый вопрос", callback_data="add_question")
        keyboard.adjust(1)
        await call.message.answer("Вы можете добавить новый вопрос:", reply_markup=keyboard.as_markup(), parse_mode='HTML')
        await state.set_state(SurveyEdit.choosing_question_to_edit)
    elif data.startswith("edit_question_"):
        question_id = int(data.replace("edit_question_", ""))
        await state.update_data(question_id=question_id)
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Изменить текст вопроса", callback_data="modify_question")
        keyboard.button(text="Удалить вопрос", callback_data="delete_question")
        keyboard.adjust(1)
        await call.message.edit_text("Что вы хотите сделать с этим вопросом?", reply_markup=keyboard.as_markup(), parse_mode='HTML')
    elif data == "modify_question":
        await call.message.edit_text("Введите новый текст вопроса.", parse_mode='HTML')
        await state.set_state(SurveyEdit.editing_question)
    elif data == "delete_question":
        data_state = await state.get_data()
        question_id = data_state.get('question_id')
        delete_question_by_id(question_id)
        await call.message.edit_text("Вопрос удален.", parse_mode='HTML')
        await state.update_data(question_id=None)
    elif data == "add_question":
        await call.message.edit_text("Введите текст нового вопроса.", parse_mode='HTML')
        await state.set_state(SurveyEdit.adding_question)
    elif data == "delete_survey":
        surveys = get_all_surveys()
        if not surveys:
            await call.message.edit_text("Опросы не найдены.", parse_mode='HTML')
            return
        keyboard = InlineKeyboardBuilder()
        for survey in surveys:
            survey_id = get_survey_id_by_name(survey)
            keyboard.button(text=survey, callback_data=f"delete_{survey_id}")
        keyboard.adjust(1)
        await call.message.edit_text("Выберите опрос для удаления:", reply_markup=keyboard.as_markup(), parse_mode='HTML')
    elif data.startswith("delete_") and data.replace("delete_", "").isdigit():
        survey_id = int(data.replace("delete_", ""))
        survey_name = get_survey_name_by_id(survey_id)
        delete_survey_by_id(survey_id)
        await call.message.edit_text(f"Опрос '{survey_name}' был удален.", parse_mode='HTML')
    elif data == "send_results":
        surveys = get_all_surveys()
        if not surveys:
            await call.message.edit_text("Опросы не найдены.", parse_mode='HTML')
            return
        keyboard = InlineKeyboardBuilder()
        for survey in surveys:
            survey_id = get_survey_id_by_name(survey)
            keyboard.button(text=survey, callback_data=f"send_results_{survey_id}")
        keyboard.adjust(1)
        await call.message.edit_text("Выберите опрос для отправки результатов:", reply_markup=keyboard.as_markup(), parse_mode='HTML')
        await state.set_state(SendResultsState.waiting_for_survey_selection)
    elif data.startswith("send_results_") and data.replace("send_results_", "").isdigit():
        survey_id = int(data.replace("send_results_", ""))
        survey_name = get_survey_name_by_id(survey_id)
        filename = f"data/survey_results_{survey_name.replace(' ', '_').replace('/', '_')}.xlsx"

        if not os.path.exists(filename):
            await call.message.edit_text(f"Результаты для опроса '{survey_name}' не найдены.", parse_mode='HTML')
            return

        file = FSInputFile(filename)
        await call.message.answer_document(file, caption=f"Результаты опроса: {survey_name}", parse_mode='HTML')
    elif data == "resend_survey":
        surveys = get_all_surveys()
        if not surveys:
            await call.message.edit_text("Опросы не найдены.", parse_mode='HTML')
            return
        keyboard = InlineKeyboardBuilder()
        for survey in surveys:
            survey_id = get_survey_id_by_name(survey)
            keyboard.button(text=survey, callback_data=f"resend_{survey_id}")
        keyboard.adjust(1)
        await call.message.edit_text("Выберите опрос для повторной отправки:", reply_markup=keyboard.as_markup(), parse_mode='HTML')
    elif data.startswith("resend_") and data.replace("resend_", "").isdigit():
        survey_id = int(data.replace("resend_", ""))
        survey_name = get_survey_name_by_id(survey_id)
        await resend_survey(call, survey_id, survey_name, bot)
    elif data.startswith("publish_") and data.replace("publish_", "").isdigit():
        survey_id = int(data.replace("publish_", ""))
        survey_name = get_survey_name_by_id(survey_id)
        await resend_survey(call, survey_id, survey_name, bot)
    else:
        await call.message.edit_text("Неизвестная команда.", parse_mode='HTML')

    await call.answer()

@router.message(SurveyCreation.waiting_for_survey_name, F.chat.type == "private")
async def survey_name_handler(message: Message, state: FSMContext):
    survey_name = message.text.strip()
    if survey_exists(survey_name):
        await message.answer(f"Опрос с названием '{survey_name}' уже существует. Введите другое название.", parse_mode='HTML')
        return
    survey_id = add_survey(survey_name)
    await state.update_data(survey_id=survey_id, survey_name=survey_name)
    await message.answer("Введите вопросы по одному. После ввода всех вопросов напишите /done", parse_mode='HTML')
    await state.set_state(SurveyCreation.waiting_for_questions)

@router.message(Command('done'), SurveyCreation.waiting_for_questions, F.chat.type == "private")
async def survey_done_handler(message: Message, state: FSMContext):
    data_state = await state.get_data()
    survey_id = data_state.get('survey_id')
    survey_name = data_state.get('survey_name')
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Опубликовать опрос", callback_data=f"publish_{survey_id}")
    keyboard.adjust(1)
    await message.answer(f"Опрос '{survey_name}' успешно создан. Хотите опубликовать его сейчас?", reply_markup=keyboard.as_markup(), parse_mode='HTML')
    await state.clear()

@router.message(SurveyCreation.waiting_for_questions, F.chat.type == "private")
async def survey_question_handler(message: Message, state: FSMContext):
    data_state = await state.get_data()
    survey_id = data_state.get('survey_id')
    question = message.text.strip()
    add_question(survey_id, question)
    await message.answer("Вопрос добавлен. Введите следующий вопрос или /done для завершения.", parse_mode='HTML')

@router.callback_query(F.data.startswith("publish_"))
async def publish_survey_handler(call: CallbackQuery, bot: Bot):
    survey_id = int(call.data.replace("publish_", ""))
    survey_name = get_survey_name_by_id(survey_id)
    await resend_survey(call, survey_id, survey_name, bot)

async def resend_survey(call: CallbackQuery, survey_id: int, survey_name: str, bot: Bot):
    groups = get_all_groups()
    if not groups:
        await call.message.edit_text("Бот не состоит ни в одной группе.", parse_mode='HTML')
        return
    bot_user = await bot.get_me()
    bot_username = bot_user.username
    for group_id, group_title in groups:
        survey_param_with_chat = f"survey_{survey_id}_{group_id}"
        deep_link = f"https://t.me/{bot_username}?start={survey_param_with_chat}"
        message_text = f"Дорогие друзья, просим вас пройти опрос: [{survey_name}]({deep_link})"
        try:
            sent_message = await bot.send_message(chat_id=group_id, text=message_text, parse_mode="Markdown")
            if survey_name != "первичный":
                await bot.pin_chat_message(chat_id=group_id, message_id=sent_message.message_id, disable_notification=False)
        except Exception as e:
            logging.error(f"Ошибка при отправке опроса в группу {group_id}: {e}")
    await call.message.edit_text(f"Опрос '{survey_name}' был успешно отправлен во все группы.", parse_mode='HTML')
    await call.answer()

@router.message(SurveyEdit.renaming_survey, F.chat.type == "private")
async def rename_survey_handler(message: Message, state: FSMContext):
    new_name = message.text.strip()
    data_state = await state.get_data()
    survey_id = data_state.get('survey_id')
    old_name = data_state.get('survey_name')

    # Обновляем название опроса в базе данных
    update_survey_name(survey_id, new_name)

    # Переименовываем файл данных, если он существует
    old_filename = f"data/survey_results_{old_name.replace(' ', '_').replace('/', '_')}.xlsx"
    new_filename = f"data/survey_results_{new_name.replace(' ', '_').replace('/', '_')}.xlsx"
    if os.path.exists(old_filename):
        os.rename(old_filename, new_filename)

    await message.answer(f"Название опроса было изменено на '{new_name}'.", parse_mode='HTML')
    await state.clear()

@router.message(SurveyEdit.editing_question, F.chat.type == "private")
async def edit_question_text_handler(message: Message, state: FSMContext):
    new_text = message.text.strip()
    data_state = await state.get_data()
    question_id = data_state.get('question_id')
    update_question_text(question_id, new_text)
    await message.answer("Текст вопроса был обновлен.", parse_mode='HTML')
    await state.update_data(question_id=None)
    await state.clear()

@router.message(SurveyEdit.adding_question, F.chat.type == "private")
async def add_new_question_handler(message: Message, state: FSMContext):
    question_text = message.text.strip()
    data_state = await state.get_data()
    survey_id = data_state.get('survey_id')
    add_question_to_survey(survey_id, question_text)
    await message.answer("Новый вопрос добавлен в опрос.", parse_mode='HTML')
    await state.clear()

def register_admin_handlers(dp: Dispatcher):
    dp.include_router(router)
