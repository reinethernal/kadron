# handlers/admin_handlers.py

import logging
import os
import re
from dotenv import load_dotenv

from aiogram import Router, Bot, Dispatcher, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InputFile
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.db_manager import (
    add_poll,
    get_all_polls,
    get_poll_id_by_name,
    delete_poll_by_id,
    get_scheduled_surveys,
    add_poll_tag,
    get_active_users,
    set_welcome_message,
    set_group_join_poll,
    get_all_groups,
    poll_exists,
    get_questions_by_poll,      # <-- Импортируем функцию для получения вопросов
)

load_dotenv()
ids = re.findall(r"\d+", os.getenv("ADMIN_IDS", ""))
ADMIN_IDS = [int(x) for x in ids]

logger = logging.getLogger(__name__)
router = Router()

# -------------------------
# Состояния для создания опроса
# -------------------------
class PollCreation(StatesGroup):
    waiting_for_poll_name = State()
    adding_question_type = State()
    adding_question_text = State()
    adding_question_options = State()
    setting_time_limit = State()
    adding_tags = State()
    scheduling_poll = State()
    setting_welcome_message = State()

# -------------------------
# Состояния для редактирования опроса
# -------------------------
class PollEdit(StatesGroup):
    choosing_poll = State()
    choosing_edit_action = State()
    renaming_poll = State()
    editing_question = State()
    choosing_question_action = State()
    editing_question_text_input = State()
    editing_question_options_input = State()
    adding_question = State()
    adding_question_type = State()
    modifying_schedule = State()

# -------------------------
# Состояние меню администратора
# -------------------------
class MenuState(StatesGroup):
    main_menu = State()

# -------------------------
# Состояния для настройки «Входного опроса»
# -------------------------
class GroupJoinPollState(StatesGroup):
    choosing_group = State()
    choosing_poll = State()

# -------------------------
# Проверка, является ли пользователь админом
# -------------------------
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# -------------------------
# Главное меню админа (ReplyKeyboardMarkup)
# -------------------------
def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать опрос"), KeyboardButton(text="Редактировать опрос")],
            [KeyboardButton(text="Просмотреть список опросов"), KeyboardButton(text="Удалить опрос")],
            [KeyboardButton(text="Отправить результаты"), KeyboardButton(text="Повторно отправить опрос")],
            [KeyboardButton(text="Запланированные опросы"), KeyboardButton(text="Фильтрация опросов")],
            [KeyboardButton(text="Настроить приветствие"), KeyboardButton(text="Тестовый режим")],
            [KeyboardButton(text="Аналитика"), KeyboardButton(text="Входной опрос")],
            [KeyboardButton(text="Вернуться в меню"), KeyboardButton(text="Выход")]
        ],
        resize_keyboard=True
    )

# -------------------------
# Команда /admin для входа в админ-меню
# -------------------------
@router.message(Command("admin"), F.chat.type == "private")
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав доступа к административным функциям.")
        return
    await message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await state.set_state(MenuState.main_menu)

# -------------------------
# Обработчик главного меню
# -------------------------
@router.message(StateFilter(MenuState.main_menu))
async def menu_handler(message: Message, state: FSMContext, bot: Bot):
    text = message.text.strip()

    if text == "Вернуться в меню":
        await state.clear()
        await admin_panel(message, state)
        return

    if text == "Создать опрос":
        await message.answer("Введите название опроса:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(PollCreation.waiting_for_poll_name)

    elif text == "Редактировать опрос":
        polls = get_all_polls()
        if not polls:
            await message.answer("Опросы не найдены.")
            await admin_panel(message, state)
            return
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=p)] for p in polls] + [[KeyboardButton(text="Вернуться в меню")]],
            resize_keyboard=True
        )
        await message.answer("Выберите опрос для редактирования:", reply_markup=kb)
        await state.set_state(PollEdit.choosing_poll)

    elif text == "Просмотреть список опросов":
        polls = get_all_polls()
        if polls:
            await message.answer("Список опросов:\n" + "\n".join(polls))
        else:
            await message.answer("Опросы не найдены.")
        await admin_panel(message, state)

    elif text == "Удалить опрос":
        polls = get_all_polls()
        if not polls:
            await message.answer("Опросы не найдены.")
            await admin_panel(message, state)
            return
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=p)] for p in polls] + [[KeyboardButton(text="Вернуться в меню")]],
            resize_keyboard=True
        )
        await message.answer("Выберите опрос для удаления:", reply_markup=kb)
        await state.update_data(action="delete_poll")
        await state.set_state(PollEdit.choosing_poll)

    elif text == "Отправить результаты":
        polls = get_all_polls()
        if not polls:
            await message.answer("Опросы не найдены.")
            await admin_panel(message, state)
            return
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=p)] for p in polls] + [[KeyboardButton(text="Вернуться в меню")]],
            resize_keyboard=True
        )
        await message.answer("Выберите опрос для отправки результатов (Excel):", reply_markup=kb)
        await state.update_data(action="send_results")
        await state.set_state(PollEdit.choosing_poll)

    elif text == "Повторно отправить опрос":
        polls = get_all_polls()
        if not polls:
            await message.answer("Опросы не найдены.")
            await admin_panel(message, state)
            return
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=p)] for p in polls] + [[KeyboardButton(text="Вернуться в меню")]],
            resize_keyboard=True
        )
        await message.answer("Выберите опрос для повторной отправки:", reply_markup=kb)
        await state.update_data(action="resend_poll")
        await state.set_state(PollEdit.choosing_poll)

    elif text == "Запланированные опросы":
        scheduled = get_scheduled_surveys()
        if scheduled:
            lines = [f"{p['name']} - {p['scheduled_time']}" for p in scheduled]
            await message.answer("Запланированные опросы:\n" + "\n".join(lines))
        else:
            await message.answer("Нет запланированных опросов.")
        await admin_panel(message, state)

    elif text == "Фильтрация опросов":
        await message.answer("Введите ключевое слово или тег для поиска опросов:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(PollCreation.adding_tags)

    elif text == "Настроить приветствие":
        await message.answer("Введите текст приветственного сообщения (используйте {username}):", reply_markup=ReplyKeyboardRemove())
        await state.set_state(PollCreation.setting_welcome_message)

    elif text == "Тестовый режим":
        from core.db_manager import set_test_mode, is_test_mode_enabled
        current = is_test_mode_enabled()
        set_test_mode(not current)
        mode = "включен" if not current else "выключен"
        await message.answer(f"Тестовый режим {mode}.")
        await admin_panel(message, state)

    elif text == "Аналитика":
        active = get_active_users()
        await message.answer(f"Активных пользователей за последние 30 дней: {active}")
        await admin_panel(message, state)

    elif text == "Входной опрос":
        groups = get_all_groups()
        if not groups:
            await message.answer("Нет зарегистрированных групп.")
            await admin_panel(message, state)
            return
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=str(g['group_id']))] for g in groups] + [[KeyboardButton(text="Вернуться в меню")]],
            resize_keyboard=True
        )
        await message.answer("Выберите группу для настройки входного опроса:", reply_markup=kb)
        await state.set_state(GroupJoinPollState.choosing_group)

    elif text == "Выход":
        await message.answer("Вы вышли из режима администратора.", reply_markup=ReplyKeyboardRemove())
        await state.clear()

    else:
        await message.answer("Неизвестная команда. Выберите действие из меню.")

# -------------------------
# Создание опроса (PollCreation)
# -------------------------

@router.message(StateFilter(PollCreation.waiting_for_poll_name))
async def poll_name_handler(message: Message, state: FSMContext):
    name = message.text.strip()
    if poll_exists(name):
        await message.answer(f"Опрос с названием '{name}' уже существует. Введите другое название.")
        return
    pid = add_poll(name)
    await state.update_data(poll_id=pid, poll_name=name)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Одиночный выбор"), KeyboardButton(text="Множественный выбор")],
            [KeyboardButton(text="Текстовый ответ"), KeyboardButton(text="Завершить создание опроса")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите тип вопроса или завершите создание опроса:", reply_markup=kb)
    await state.set_state(PollCreation.adding_question_type)

@router.message(StateFilter(PollCreation.adding_question_type))
async def poll_question_type_handler(message: Message, state: FSMContext):
    text = message.text.strip()
    if text in ["Одиночный выбор", "Множественный выбор", "Текстовый ответ"]:
        await state.update_data(question_type=text)
        await message.answer("Введите текст вопроса:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(PollCreation.adding_question_text)
    elif text == "Завершить создание опроса":
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Установить время окончания")],
                [KeyboardButton(text="Сделать опрос анонимным")],
                [KeyboardButton(text="Добавить теги")],
                [KeyboardButton(text="Запланировать отправку")],
                [KeyboardButton(text="Завершить")]
            ],
            resize_keyboard=True
        )
        await message.answer("Настройте опрос перед завершением:", reply_markup=kb)
        await state.set_state(PollCreation.setting_time_limit)
    else:
        await message.answer("Пожалуйста, выберите тип вопроса из меню.")

@router.message(StateFilter(PollCreation.adding_question_text))
async def poll_question_text_handler(message: Message, state: FSMContext):
    qtext = message.text.strip()
    await state.update_data(question_text=qtext)
    data = await state.get_data()
    qtype = data.get('question_type')
    pid = data.get('poll_id')
    if qtype in ["Одиночный выбор", "Множественный выбор"]:
        await message.answer("Введите варианты ответов через запятую:")
        await state.set_state(PollCreation.adding_question_options)
    else:
        from core.db_manager import add_question_to_poll
        add_question_to_poll(pid, qtext, qtype)
        await message.answer("Вопрос добавлен.")
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Одиночный выбор"), KeyboardButton(text="Множественный выбор")],
                [KeyboardButton(text="Текстовый ответ"), KeyboardButton(text="Завершить создание опроса")]
            ],
            resize_keyboard=True
        )
        await message.answer("Выберите следующий тип вопроса или завершите создание опроса:", reply_markup=kb)
        await state.set_state(PollCreation.adding_question_type)

@router.message(StateFilter(PollCreation.adding_question_options))
async def poll_question_options_handler(message: Message, state: FSMContext):
    opts = [o.strip() for o in message.text.split(',')]
    data = await state.get_data()
    pid = data.get('poll_id')
    qtext = data.get('question_text')
    qtype = data.get('question_type')
    from core.db_manager import add_question_to_poll
    add_question_to_poll(pid, qtext, qtype, opts)
    await message.answer("Вопрос с вариантами ответов добавлен.")
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Одиночный выбор"), KeyboardButton(text="Множественный выбор")],
            [KeyboardButton(text="Текстовый ответ"), KeyboardButton(text="Завершить создание опроса")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите следующий тип вопроса или завершите создание опроса:", reply_markup=kb)
    await state.set_state(PollCreation.adding_question_type)

@router.message(StateFilter(PollCreation.setting_time_limit))
async def poll_settings_handler(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    pid = data.get('poll_id')
    if text == "Установить время окончания":
        await message.answer("Введите количество часов до окончания опроса:")
    elif text == "Сделать опрос анонимным":
        from core.db_manager import update_poll_anonymous
        update_poll_anonymous(pid, True)
        await message.answer("Опрос будет анонимным.")
    elif text == "Добавить теги":
        await message.answer("Введите теги через запятую:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(PollCreation.adding_tags)
    elif text == "Запланировать отправку":
        await message.answer("Введите дату и время отправки в формате ДД.ММ.ГГГГ ЧЧ:ММ:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(PollCreation.scheduling_poll)
    elif text == "Завершить":
        await message.answer("Опрос создан.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        await admin_panel(message, state)
    else:
        try:
            from datetime import datetime, timedelta
            hours = int(text)
            tlimit = datetime.now() + timedelta(hours=hours)
            from core.db_manager import update_poll_time_limit
            update_poll_time_limit(pid, tlimit)
            await message.answer(f"Время окончания опроса установлено на {tlimit.strftime('%d.%m.%Y %H:%M')}.")
        except ValueError:
            await message.answer("Пожалуйста, выберите действие из меню или введите число часов.")

@router.message(StateFilter(PollCreation.adding_tags))
async def poll_adding_tags_handler(message: Message, state: FSMContext):
    tags = [t.strip() for t in message.text.split(',')]
    data = await state.get_data()
    pid = data.get('poll_id')
    for tag in tags:
        add_poll_tag(pid, tag)
    await message.answer("Теги добавлены.")
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Установить время окончания")],
            [KeyboardButton(text="Сделать опрос анонимным")],
            [KeyboardButton(text="Добавить теги")],
            [KeyboardButton(text="Запланировать отправку")],
            [KeyboardButton(text="Завершить")]
        ],
        resize_keyboard=True
    )
    await message.answer("Настройте опрос:", reply_markup=kb)
    await state.set_state(PollCreation.setting_time_limit)

@router.message(StateFilter(PollCreation.scheduling_poll))
async def poll_scheduling_handler(message: Message, state: FSMContext):
    from datetime import datetime
    try:
        sched_time = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
        data = await state.get_data()
        pid = data.get('poll_id')
        from core.db_manager import schedule_poll
        schedule_poll(pid, sched_time)
        await message.answer(f"Опрос будет отправлен {sched_time.strftime('%d.%m.%Y %H:%M')}.")
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Установить время окончания")],
                [KeyboardButton(text="Сделать опрос анонимным")],
                [KeyboardButton(text="Добавить теги")],
                [KeyboardButton(text="Запланировать отправку")],
                [KeyboardButton(text="Завершить")]
            ],
            resize_keyboard=True
        )
        await message.answer("Настройте опрос:", reply_markup=kb)
        await state.set_state(PollCreation.setting_time_limit)
    except ValueError:
        await message.answer("Неверный формат даты и времени. Введите в формате ДД.ММ.ГГГГ ЧЧ:ММ.")

@router.message(StateFilter(PollCreation.setting_welcome_message))
async def poll_welcome_handler(message: Message, state: FSMContext):
    text = message.text.strip()
    set_welcome_message(text)
    await message.answer("Приветственное сообщение обновлено.")
    await state.clear()
    await admin_panel(message, state)

# -------------------------
# Редактирование опроса (PollEdit)
# -------------------------
@router.message(StateFilter(PollEdit.choosing_poll))
async def poll_edit_choosing_handler(message: Message, state: FSMContext, bot: Bot):
    poll_name = message.text.strip()
    if poll_name == "Вернуться в меню":
        await state.clear()
        await admin_panel(message, state)
        return
    if not poll_exists(poll_name):
        await message.answer("Такой опрос не найден. Выберите из списка.")
        return
    pid = get_poll_id_by_name(poll_name)
    await state.update_data(poll_id=pid, poll_name=poll_name)
    action = (await state.get_data()).get('action')
    if action == "delete_poll":
        delete_poll_by_id(pid)
        await message.answer("Опрос удален.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        await admin_panel(message, state)
    elif action == "send_results":
        sanitized_name = poll_name.replace(" ", "_").replace("/", "_")
        filename = f"data/survey_results_{sanitized_name}.xlsx"
        if os.path.exists(filename):
            await bot.send_document(message.from_user.id, InputFile(filename))
        else:
            await message.answer("Результаты для этого опроса отсутствуют.")
        await state.clear()
        await admin_panel(message, state)
    elif action == "resend_poll":
        from plugins.admin_plugin import send_survey_to_users
        await send_survey_to_users(pid, bot)
        await message.answer(f"Опрос '{poll_name}' повторно отправлен.")
        await state.clear()
        await admin_panel(message, state)
    else:
        # Используем get_questions_by_poll из core/db_manager вместо get_questions
        questions = get_questions_by_poll(pid)
        if not questions:
            await message.answer("В этом опросе нет вопросов.")
            await admin_panel(message, state)
            return
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=q['text'])] for q in questions
            ] + [
                [KeyboardButton(text="Добавить вопрос")],
                [KeyboardButton(text="Вернуться в меню")]
            ],
            resize_keyboard=True
        )
        await message.answer(
            f"Вы выбрали опрос '{poll_name}'. Выберите вопрос для редактирования или добавьте новый:",
            reply_markup=kb
        )
        await state.update_data(questions=questions)
        await state.set_state(PollEdit.editing_question)

@router.message(StateFilter(PollEdit.editing_question))
async def poll_editing_question_handler(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    if text == "Добавить вопрос":
        await message.answer("Введите текст нового вопроса:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(PollEdit.adding_question)
    elif text == "Вернуться в меню":
        await state.clear()
        await admin_panel(message, state)
    else:
        questions = data.get('questions', [])
        selected = next((q for q in questions if q['text'] == text), None)
        if not selected:
            await message.answer("Не удалось найти вопрос. Пожалуйста, выберите из списка.")
            return
        await state.update_data(question_id=selected['id'])
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Изменить текст вопроса"), KeyboardButton(text="Изменить варианты ответов")],
                [KeyboardButton(text="Удалить вопрос"), KeyboardButton(text="Вернуться в меню")]
            ],
            resize_keyboard=True
        )
        await message.answer(f"Вы выбрали вопрос: {selected['text']}. Что будем делать?", reply_markup=kb)
        await state.set_state(PollEdit.choosing_question_action)

@router.message(StateFilter(PollEdit.choosing_question_action))
async def poll_choosing_question_action_handler(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    question_id = data.get("question_id")

    if text == "Изменить текст вопроса":
        await message.answer("Введите новый текст вопроса:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(PollEdit.editing_question_text_input)
    elif text == "Изменить варианты ответов":
        await message.answer("Введите новые варианты ответов через запятую:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(PollEdit.editing_question_options_input)
    elif text == "Удалить вопрос":
        if question_id:
            from core.db_manager import delete_question_by_id
            delete_question_by_id(question_id)
            await message.answer("Вопрос удалён.")
        else:
            await message.answer("Не найден question_id для удаления.")
        await state.clear()
        await admin_panel(message, state)
    elif text == "Вернуться в меню":
        await state.clear()
        await admin_panel(message, state)
    else:
        await message.answer("Пожалуйста, выберите действие из меню.")

@router.message(StateFilter(PollEdit.editing_question_text_input))
async def poll_editing_question_text_input_handler(message: Message, state: FSMContext):
    new_text = message.text.strip()
    data = await state.get_data()
    question_id = data.get("question_id")
    if question_id:
        from core.db_manager import update_question_text
        update_question_text(question_id, new_text)
        await message.answer("Текст вопроса обновлён.")
    else:
        await message.answer("Не найден question_id для редактирования текста.")
    await state.clear()
    await admin_panel(message, state)

@router.message(StateFilter(PollEdit.editing_question_options_input))
async def poll_editing_question_options_input_handler(message: Message, state: FSMContext):
    new_options = [o.strip() for o in message.text.split(',')]
    data = await state.get_data()
    question_id = data.get("question_id")
    if question_id:
        from core.db_manager import update_question_options
        update_question_options(question_id, new_options)
        await message.answer("Варианты ответа обновлены.")
    else:
        await message.answer("Не найден question_id для редактирования вариантов.")
    await state.clear()
    await admin_panel(message, state)

@router.message(StateFilter(PollEdit.adding_question))
async def poll_adding_question_handler(message: Message, state: FSMContext):
    new_text = message.text.strip()
    await state.update_data(question_text=new_text)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Одиночный выбор"), KeyboardButton(text="Множественный выбор")],
            [KeyboardButton(text="Текстовый ответ")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите тип вопроса:", reply_markup=kb)
    await state.set_state(PollEdit.adding_question_type)

@router.message(StateFilter(PollEdit.adding_question_type))
async def poll_adding_question_type_handler(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    pid = data.get("poll_id")
    new_text = data.get("question_text")

    if text in ["Одиночный выбор", "Множественный выбор", "Текстовый ответ"]:
        if text in ["Одиночный выбор", "Множественный выбор"]:
            await state.update_data(question_type=text)
            await message.answer("Введите новые варианты ответов через запятую:", reply_markup=ReplyKeyboardRemove())
            await state.set_state(PollEdit.editing_question_options_input)
        else:
            # Текстовый ответ
            from core.db_manager import add_question_to_poll
            add_question_to_poll(pid, new_text, text)
            await message.answer("Новый вопрос (текстовый) добавлен.")
            await state.clear()
            await admin_panel(message, state)
    else:
        await message.answer("Пожалуйста, выберите тип вопроса из меню.")

@router.message(StateFilter(PollEdit.modifying_schedule))
async def poll_modifying_schedule_handler(message: Message, state: FSMContext):
    from datetime import datetime
    data = await state.get_data()
    pid = data.get("poll_id")

    try:
        sched_time = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
        from core.db_manager import schedule_poll
        schedule_poll(pid, sched_time)
        await message.answer(f"Время отправки опроса обновлено на {sched_time.strftime('%d.%m.%Y %H:%M')}.")
        await state.clear()
        await admin_panel(message, state)
    except ValueError:
        await message.answer("Неверный формат даты и времени. Введите в формате ДД.ММ.ГГГГ ЧЧ:ММ.")

# -------------------------
# Настройка «Входного» опроса для группы
# -------------------------
@router.message(StateFilter(GroupJoinPollState.choosing_group))
async def choose_join_poll_group_handler(message: Message, state: FSMContext):
    if message.text == "Вернуться в меню":
        await state.clear()
        await admin_panel(message, state)
        return
    try:
        group_id = int(message.text)
    except ValueError:
        await message.answer("Некорректный ID группы. Повторите ввод или вернитесь в меню.")
        return
    await state.update_data(selected_group_id=group_id)

    polls = get_all_polls()
    if not polls:
        await message.answer("Опросы не найдены.")
        await admin_panel(message, state)
        return
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=p)] for p in polls] + [[KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    )
    await message.answer("Выберите опрос, который будет отправлен при вступлении новых участников:", reply_markup=kb)
    await state.set_state(GroupJoinPollState.choosing_poll)

@router.message(StateFilter(GroupJoinPollState.choosing_poll))
async def choose_join_poll_name_handler(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await admin_panel(message, state)
        return
    poll_name = message.text.strip()
    pid = get_poll_id_by_name(poll_name)
    if not pid:
        await message.answer("Такого опроса не найдено. Повторите выбор или нажмите 'Отмена'.")
        return
    data = await state.get_data()
    group_id = data.get("selected_group_id")
    if not group_id:
        await message.answer("Ошибка: не удалось определить группу.")
        await state.clear()
        await admin_panel(message, state)
        return

    set_group_join_poll(group_id, pid)
    await message.answer(f"Входной опрос для группы {group_id} установлен: '{poll_name}' (ID={pid}).")
    await state.clear()
    await admin_panel(message, state)

# -------------------------
# Регистрация роутера
# -------------------------
def register_admin_handlers(dp: Dispatcher):
    dp.include_router(router)
