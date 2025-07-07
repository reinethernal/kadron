"""
Плагин планирования для Telegram‑бота (aiogram 3.x).

Обеспечивает возможность планировать опросы и другие задачи,
а также управление напоминаниями и выполнением запланированных действий.
"""

import asyncio
import datetime
import logging
import re
from core.db_manager import get_all_groups

from aiogram import Dispatcher, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext  # <-- Вместо dispatcher.FSMContext
from aiogram.fsm.state import StatesGroup, State  # <-- Вместо dispatcher.filters.state
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Если используем собственное хранилище (storage_plugin)
try:
    from .storage_plugin import storage
except ImportError:
    # Для тестов, fallback
    class DummyStorage:
        def get_survey(self, survey_id):
            return {}

        def save_survey(self, survey_id, data):
            pass

        def get_setting(self, key, default=None):
            return default

        def set_setting(self, key, value):
            pass

    storage = DummyStorage()

logger = logging.getLogger(__name__)
scheduler_instance = None


class SchedulerStates(StatesGroup):
    """Состояния (States) для функционала планирования"""

    SELECTING_SURVEY = State()
    SELECTING_GROUPS = State()
    SELECTING_DATE = State()
    SELECTING_TIME = State()
    CONFIRMING = State()


class SchedulerPlugin:
    """Плагин для планирования опросов и отправки сообщений по расписанию"""

    def __init__(self, bot: "Bot"):
        self.name = "scheduler_plugin"
        self.description = "Планирование отправки опросов"
        self.scheduled_tasks = {}
        self.reminder_tasks = {}
        self.close_tasks = {}
        self.bot = bot

    async def register_handlers(self, dp: Dispatcher):
        """
        Регистрируем хендлеры (обработчики) в стиле aiogram 3.x
        """

        # Вместо dp.register_message_handler(...), используем dp.message.register(...)
        dp.message.register(
            self.cmd_schedule,
            Command(commands=["schedule"]),  # Разрешаем команду /schedule
        )

        # Вместо dp.register_callback_query_handler(...), используем dp.callback_query.register(...)
        # Дополнительно учитываем, что нам нужно вызывать этот хендлер в состоянии SchedulerStates.SELECTING_SURVEY
        dp.callback_query.register(
            self.handle_survey_selection,
            lambda c: c.data.startswith("schedule_survey_"),
            SchedulerStates.SELECTING_SURVEY,
        )

        dp.message.register(self.process_group_input, SchedulerStates.SELECTING_GROUPS)

        # Хендлер на ввод даты (состояние SELECTING_DATE)
        dp.message.register(self.process_date_input, SchedulerStates.SELECTING_DATE)

        # Хендлер на ввод времени (состояние SELECTING_TIME)
        dp.message.register(self.process_time_input, SchedulerStates.SELECTING_TIME)

        # Хендлер на подтверждение планирования (callback) в состоянии CONFIRMING
        dp.callback_query.register(
            self.handle_confirmation,
            lambda c: c.data.startswith("schedule_confirm_"),
            SchedulerStates.CONFIRMING,
        )

        # Команда /scheduled (без конкретного состояния)
        dp.message.register(self.cmd_list_scheduled, Command(commands=["scheduled"]))

        # Хендлер на отмену запланированного (любой стейт, или без стейта)
        dp.callback_query.register(
            self.handle_cancel_scheduled,
            lambda c: c.data.startswith("cancel_scheduled_"),
        )

    def get_commands(self):
        """Возвращаем список команд, которые добавляет этот плагин (для /help и т.п.)"""
        return [
            types.BotCommand(
                command="schedule", description="Запланировать отправку опроса"
            ),
            types.BotCommand(
                command="scheduled", description="Список запланированных опросов"
            ),
        ]

    async def cmd_schedule(self, message: types.Message, state: FSMContext):
        """Обработка команды /schedule — начать процесс планирования опроса"""
        logger.debug(f"{message.text} from {message.from_user.id}")

        user_id = message.from_user.id
        all_surveys = storage.get_all_surveys()

        # Фильтруем опросы, созданные этим пользователем и которые активны
        user_surveys = {
            survey_id: s
            for survey_id, s in all_surveys.items()
            if s.get("creator_id") == user_id and s.get("status") == "active"
        }

        if not user_surveys:
            await message.answer("У вас нет активных опросов для планирования.")
            return

        # Формируем клавиатуру со списком опросов
        builder = InlineKeyboardBuilder()
        for survey_id, survey in user_surveys.items():
            btn_text = survey.get("title", "Без названия")
            builder.button(text=btn_text, callback_data=f"schedule_survey_{survey_id}")
        builder.adjust(1)
        markup = builder.as_markup()

        await message.answer(
            "Выберите опрос для планирования отправки:", reply_markup=markup
        )
        # Устанавливаем состояние — ожидаем, что пользователь выберет опрос
        await state.set_state(SchedulerStates.SELECTING_SURVEY)

    async def handle_survey_selection(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Обработка выбора опроса, который хотим запланировать"""
        survey_id = callback_query.data.split("_")[2]
        survey = storage.get_survey(survey_id)

        if not survey:
            await callback_query.answer("Опрос не найден.")
            await state.clear()  # сбрасываем состояние
            return

        # Сохраняем ID опроса в данные стейта
        await state.update_data(selected_survey_id=survey_id)

        groups = get_all_groups()
        text = "Выберите группы для отправки (ID через пробел):\n"
        if groups:
            for g in groups:
                text += f"{g['group_id']}: {g['title']}\n"
        else:
            text += "(нет доступных групп)"

        await state.set_state(SchedulerStates.SELECTING_GROUPS)
        await callback_query.message.edit_text(
            f"Выбран опрос: {survey.get('title', 'Без названия')}\n\n" + text
        )
        await callback_query.answer()

    async def process_group_input(self, message: types.Message, state: FSMContext):
        """Сохраняем выбранные группы и переходим к выбору даты"""
        ids = [int(x) for x in re.findall(r"\d+", message.text)]
        data = await state.get_data()
        survey_id = data.get("selected_survey_id")
        if survey_id:
            survey = storage.get_survey(survey_id)
            if survey is not None:
                survey["target_chats"] = ids
                storage.save_survey(survey_id, survey)

        await state.update_data(target_chats=ids)
        await message.answer(
            "Введите дату для отправки в формате ДД.ММ.ГГГГ (например, 31.12.2025):"
        )
        await state.set_state(SchedulerStates.SELECTING_DATE)

    async def process_date_input(self, message: types.Message, state: FSMContext):
        """Принимаем дату от пользователя"""
        date_str = message.text.strip()

        try:
            day, month, year = map(int, date_str.split("."))
            selected_date = datetime.date(year, month, day)

            # Дата должна быть в будущем
            if selected_date < datetime.date.today():
                await message.answer("Пожалуйста, выберите дату в будущем.")
                return

            await state.update_data(selected_date=selected_date.isoformat())
            await message.answer(
                f"Выбрана дата: {selected_date.strftime('%d.%m.%Y')}\n\n"
                "Теперь введите время в формате ЧЧ:ММ (например, 14:30):"
            )
            await state.set_state(SchedulerStates.SELECTING_TIME)

        except (ValueError, IndexError):
            await message.answer(
                "Неверный формат даты. Используйте ДД.ММ.ГГГГ (например, 31.12.2025)."
            )

    async def process_time_input(self, message: types.Message, state: FSMContext):
        """Принимаем время от пользователя"""
        time_str = message.text.strip()

        try:
            hour, minute = map(int, time_str.split(":"))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                await message.answer("Часы: 0–23, минуты: 0–59. Повторите ввод:")
                return

            # Получаем дату из стейта
            data = await state.get_data()
            date_str = data.get("selected_date")
            survey_id = data.get("selected_survey_id")

            if not date_str or not survey_id:
                await message.answer("Произошла ошибка. Начните заново.")
                await state.clear()
                return

            selected_date = datetime.date.fromisoformat(date_str)
            selected_datetime = datetime.datetime.combine(
                selected_date, datetime.time(hour, minute)
            )

            if selected_datetime <= datetime.datetime.now():
                await message.answer("Это время уже прошло. Введите будущее время.")
                return

            # Сохраняем в стейт
            await state.update_data(
                selected_time=f"{hour:02d}:{minute:02d}",
                selected_datetime=selected_datetime.isoformat(),
            )

            # Предлагаем подтвердить
            builder = InlineKeyboardBuilder()
            builder.button(
                text="✅ Подтвердить", callback_data=f"schedule_confirm_yes_{survey_id}"
            )
            builder.button(text="❌ Отменить", callback_data="schedule_confirm_no")
            builder.adjust(2)
            markup = builder.as_markup()

            await message.answer(
                f"Подтвердите планирование:\n\n"
                f"Опрос: {storage.get_survey(survey_id).get('title', 'Без названия')}\n"
                f"Дата: {selected_date.strftime('%d.%m.%Y')}\n"
                f"Время: {hour:02d}:{minute:02d}\n\n"
                "Опрос будет отправлен автоматически в указанное время.",
                reply_markup=markup,
            )
            await state.set_state(SchedulerStates.CONFIRMING)

        except (ValueError, IndexError):
            await message.answer(
                "Неверный формат времени. Используйте ЧЧ:ММ (например, 14:30)."
            )

    async def handle_confirmation(
        self, callback_query: types.CallbackQuery, state: FSMContext
    ):
        """Подтверждаем или отменяем планирование"""
        action = callback_query.data.split("_")[2]

        if action == "no":
            await callback_query.message.edit_text("Планирование отменено.")
            await state.clear()
            await callback_query.answer()
            return

        data = await state.get_data()
        survey_id = data.get("selected_survey_id")
        datetime_str = data.get("selected_datetime")

        if not survey_id or not datetime_str:
            await callback_query.message.edit_text("Ошибка. Начните заново.")
            await state.clear()
            await callback_query.answer()
            return

        scheduled_datetime = datetime.datetime.fromisoformat(datetime_str)
        scheduled_surveys = storage.get_setting("scheduled_surveys", [])

        scheduled_surveys.append(
            {
                "survey_id": survey_id,
                "scheduled_time": datetime_str,
                "created_by": callback_query.from_user.id,
                "created_at": datetime.datetime.now().isoformat(),
            }
        )
        storage.set_setting("scheduled_surveys", scheduled_surveys)

        # Создаём задачу на выполнение
        self._create_scheduled_task(survey_id, scheduled_datetime)

        await callback_query.message.edit_text(
            f"✅ Опрос запланирован на {scheduled_datetime.strftime('%d.%m.%Y %H:%M')}."
        )
        await state.clear()
        await callback_query.answer()

    def _create_scheduled_task(self, survey_id, scheduled_time):
        """Создаём asyncio-задачи для отправки и напоминания"""
        now = datetime.datetime.now()
        time_delta = (scheduled_time - now).total_seconds()
        if time_delta <= 0:
            logger.warning(f"Запланированное время для опроса {survey_id} уже прошло")
            return

        # Основная задача
        task = asyncio.create_task(self._send_scheduled_survey(survey_id, time_delta))
        self.scheduled_tasks[survey_id] = task

        survey = storage.get_survey(survey_id)
        if survey:
            try:
                deadline = datetime.datetime.fromisoformat(survey.get("deadline"))
                reminder_time = deadline - datetime.timedelta(minutes=10)
                reminder_delta = (reminder_time - now).total_seconds()
                if reminder_delta > 0:
                    reminder_task = asyncio.create_task(
                        self._send_reminder(survey_id, reminder_delta)
                    )
                    self.reminder_tasks[survey_id] = reminder_task
            except Exception as e:
                logger.error(
                    f"Не удалось запланировать напоминание для опроса {survey_id}: {e}"
                )

    async def _send_scheduled_survey(self, survey_id, delay_seconds):
        """Ждём delay_seconds, затем отправляем опрос"""
        try:
            await asyncio.sleep(delay_seconds)
            survey = storage.get_survey(survey_id)
            if not survey:
                logger.error(f"Scheduled survey {survey_id} not found")
                return

            # Помечаем опрос как активный, если он ещё не активен
            if survey.get("status") != "active":
                survey["status"] = "active"
                storage.save_survey(survey_id, survey)

            # Берём список чатов, куда рассылать
            target_chats = survey.get("target_chats", [])
            if not target_chats:
                logger.warning(
                    f"Нет целевых чатов для запланированного опроса {survey_id}"
                )
                return

            # Используем сохранённый экземпляр бота
            bot = self.bot

            # Отправляем опрос в каждый чат
            for chat_id in target_chats:
                try:
                    builder = InlineKeyboardBuilder()
                    username = getattr(bot, "username", None)
                    if not username:
                        try:
                            me = await bot.get_me()
                            username = getattr(me, "username", "")
                        except Exception:
                            username = ""
                    url_base = (
                        f"https://t.me/{username}" if username else "https://t.me"
                    )
                    url = f"{url_base}?start=survey_{survey_id}"
                    builder.button(
                        text="Пройти опрос",
                        url=url,
                    )
                    markup = builder.as_markup()
                    msg = await bot.send_message(
                        chat_id,
                        f"📊 Новый опрос: {survey.get('title')}\n\n{survey.get('description', '')}",
                        reply_markup=markup,
                    )
                    await self._try_pin(chat_id, msg.message_id)
                except Exception as e:
                    logger.error(f"Не удалось отправить опрос в чат {chat_id}: {e}")

            # Удаляем запись о запланированном опросе, так как он уже отправлен
            scheduled_surveys = storage.get_setting("scheduled_surveys", [])
            scheduled_surveys = [
                s for s in scheduled_surveys if s.get("survey_id") != survey_id
            ]
            storage.set_setting("scheduled_surveys", scheduled_surveys)

            # Планируем закрытие опроса
            try:
                deadline = datetime.datetime.fromisoformat(survey.get("deadline"))
                close_delta = (deadline - datetime.datetime.now()).total_seconds()
                if close_delta > 0:
                    close_task = asyncio.create_task(
                        self._close_survey(survey_id, close_delta)
                    )
                    self.close_tasks[survey_id] = close_task
            except Exception as e:
                logger.error(
                    f"Не удалось запланировать закрытие опроса {survey_id}: {e}"
                )

            logger.info(f"Запланированный опрос {survey_id} успешно отправлен")

        except asyncio.CancelledError:
            logger.info(f"Задача отправки опроса {survey_id} была отменена")
        except Exception as e:
            logger.error(f"Ошибка в задаче отправки опроса {survey_id}: {e}")

    async def _send_reminder(self, survey_id, delay_seconds):
        """Отправляем напоминание за 10 минут до окончания опроса"""
        try:
            await asyncio.sleep(delay_seconds)
            survey = storage.get_survey(survey_id)
            if not survey:
                logger.error(f"Survey {survey_id} for reminder not found")
                return

            bot = self.bot
            target_chats = survey.get("target_chats", [])

            # Рассылаем напоминания по чатам
            for chat_id in target_chats:
                try:
                    await bot.send_message(
                        chat_id,
                        f"⏰ Напоминание: опрос \"{survey.get('title')}\" будет закрыт через 10 минут!",
                    )
                except Exception as e:
                    logger.error(
                        f"Не удалось отправить напоминание в чат {chat_id}: {e}"
                    )

        except asyncio.CancelledError:
            logger.info(f"Задача напоминания для опроса {survey_id} была отменена")
        except Exception as e:
            logger.error(f"Ошибка в задаче напоминания для опроса {survey_id}: {e}")

    async def _close_survey(self, survey_id, delay_seconds):
        """Закрывает опрос по истечении срока"""
        try:
            await asyncio.sleep(delay_seconds)
            survey = storage.get_survey(survey_id)
            if not survey or survey.get("status") != "active":
                return
            survey["status"] = "closed"
            storage.save_survey(survey_id, survey)
            logger.info(f"Опрос {survey_id} закрыт по истечении срока")
        except asyncio.CancelledError:
            logger.info(f"Задача закрытия опроса {survey_id} была отменена")
        except Exception as e:
            logger.error(f"Ошибка при закрытии опроса {survey_id}: {e}")

    async def _try_pin(self, chat_id: int, message_id: int):
        """Пытается закрепить сообщение, если у бота есть такие права"""
        try:
            me = await self.bot.get_me()
            member = await self.bot.get_chat_member(chat_id, me.id)
            can_pin = (
                getattr(member, "can_pin_messages", False) or member.status == "creator"
            )
            if can_pin:
                await self.bot.pin_chat_message(
                    chat_id=chat_id, message_id=message_id, disable_notification=False
                )
            else:
                logger.warning(f"У бота нет прав закреплять сообщения в чате {chat_id}")
        except Exception as e:
            logger.error(f"Не удалось закрепить сообщение в чате {chat_id}: {e}")

    async def cmd_list_scheduled(self, message: types.Message):
        """Обработка команды /scheduled — список запланированных опросов для данного пользователя"""
        logger.debug(f"{message.text} from {message.from_user.id}")
        user_id = message.from_user.id
        scheduled_surveys = storage.get_setting("scheduled_surveys", [])

        # Оставляем только те, что созданы этим пользователем
        user_scheduled = [
            s for s in scheduled_surveys if s.get("created_by") == user_id
        ]

        if not user_scheduled:
            await message.answer("У вас нет запланированных опросов.")
            return

        text = "📅 Ваши запланированные опросы:\n\n"
        builder = InlineKeyboardBuilder()

        for i, scheduled in enumerate(user_scheduled):
            sid = scheduled.get("survey_id")
            survey = storage.get_survey(sid)
            if not survey:
                continue

            scheduled_time = datetime.datetime.fromisoformat(
                scheduled.get("scheduled_time")
            )
            text += f"{i+1}. {survey.get('title')}\n"
            text += f"   📆 {scheduled_time.strftime('%d.%m.%Y %H:%M')}\n\n"
            builder.button(
                text=f"❌ Отменить: {survey.get('title')}",
                callback_data=f"cancel_scheduled_{sid}",
            )

        builder.adjust(1)
        markup = builder.as_markup()

        await message.answer(text, reply_markup=markup)

    async def handle_cancel_scheduled(self, callback_query: types.CallbackQuery):
        """Отмена запланированного опроса"""
        survey_id = callback_query.data.split("_")[2]
        user_id = callback_query.from_user.id

        scheduled_surveys = storage.get_setting("scheduled_surveys", [])
        for i, scheduled in enumerate(scheduled_surveys):
            if (
                scheduled.get("survey_id") == survey_id
                and scheduled.get("created_by") == user_id
            ):
                del scheduled_surveys[i]

                # Отменяем задачи, если они существуют
                if survey_id in self.scheduled_tasks:
                    self.scheduled_tasks[survey_id].cancel()
                    del self.scheduled_tasks[survey_id]

                if survey_id in self.reminder_tasks:
                    self.reminder_tasks[survey_id].cancel()
                    del self.reminder_tasks[survey_id]

                storage.set_setting("scheduled_surveys", scheduled_surveys)
                await callback_query.message.edit_text(
                    "✅ Запланированный опрос отменен."
                )
                await callback_query.answer("Опрос отменен")
                return

        await callback_query.answer("Опрос не найден или у вас нет прав для его отмены")

    def on_plugin_load(self):
        """Вызывается при загрузке плагина"""
        logger.info("Плагин планировщика загружен")

        # Загружаем запланированные опросы из хранилища и восстанавливаем задачи
        scheduled_surveys = storage.get_setting("scheduled_surveys", [])
        for scheduled in scheduled_surveys:
            try:
                sid = scheduled.get("survey_id")
                scheduled_time = datetime.datetime.fromisoformat(
                    scheduled.get("scheduled_time")
                )
                if scheduled_time > datetime.datetime.now():
                    self._create_scheduled_task(sid, scheduled_time)
            except Exception as e:
                logger.error(f"Не удалось загрузить запланированный опрос: {e}")

    def on_plugin_unload(self):
        """Вызывается при выгрузке плагина"""
        # Отменяем все задачи
        for task in self.scheduled_tasks.values():
            task.cancel()
        for task in self.reminder_tasks.values():
            task.cancel()
        for task in self.close_tasks.values():
            task.cancel()

        logger.info("Плагин планировщика выгружен")


def load_plugin(bot: Bot):
    """Функция для загрузки плагина (aiogram-style)"""
    global scheduler_instance
    scheduler_instance = SchedulerPlugin(bot)
    return scheduler_instance
