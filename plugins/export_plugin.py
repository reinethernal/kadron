import logging
import json
import csv
import io
import datetime
import os

from aiogram import Dispatcher, types
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Импорт хранилища
try:
    from .storage_plugin import storage
except ImportError:
    class DummyStorage:
        def get_survey(self, survey_id): return {}
        def get_all_surveys(self): return {}
    storage = DummyStorage()

# Импорт ролей для проверки прав
try:
    from .roles_plugin import RolesPlugin
    roles_plugin = RolesPlugin()
    has_permission = roles_plugin.has_permission
except ImportError:
    def has_permission(user_id, permission):
        admin_ids = storage.get_setting("admin_ids", [])
        return user_id in admin_ids

logger = logging.getLogger(__name__)

class ExportPlugin:
    def __init__(self):
        self.name = "export_plugin"
        self.description = "Экспорт данных опросов в разные форматы"

    async def register_handlers(self, dp: Dispatcher):
        # Используем новые методы регистрации:
        from aiogram.filters import Command  # фильтр команд из aiogram v3
        dp.message.register(self.cmd_export, Command("export"))
        dp.callback_query.register(
            self.handle_survey_selection,
            lambda c: c.data.startswith("export_survey_")
        )
        dp.callback_query.register(
            self.handle_format_selection,
            lambda c: c.data.startswith("export_format_")
        )

    def get_commands(self):
        return [types.BotCommand(command="export", description="Экспорт данных опросов")]

    async def cmd_export(self, message: types.Message):
        logger.debug(f"{message.text} from {message.from_user.id}")
        user_id = message.from_user.id
        all_surveys = storage.get_all_surveys()
        if not all_surveys:
            await message.answer("Нет доступных опросов для экспорта.")
            return
        builder = InlineKeyboardBuilder()
        for survey_id, survey in all_surveys.items():
            if survey.get("creator_id") == user_id or has_permission(user_id, "export_data"):
                builder.button(
                    text=survey.get("title", "Без названия"),
                    callback_data=f"export_survey_{survey_id}"
                )
        builder.adjust(1)
        markup = builder.as_markup()
        await message.answer("Выберите опрос для экспорта данных:", reply_markup=markup)

    async def handle_survey_selection(self, callback_query: types.CallbackQuery):
        survey_id = callback_query.data.split("_")[2]
        builder = InlineKeyboardBuilder()
        builder.button(text="CSV", callback_data=f"export_format_csv_{survey_id}")
        builder.button(text="JSON", callback_data=f"export_format_json_{survey_id}")
        builder.button(text="Excel", callback_data=f"export_format_excel_{survey_id}")
        builder.button(text="Текстовый отчет", callback_data=f"export_format_text_{survey_id}")
        builder.adjust(2)
        markup = builder.as_markup()
        await callback_query.message.edit_text("Выберите формат экспорта:", reply_markup=markup)
        await callback_query.answer()

    async def handle_format_selection(self, callback_query: types.CallbackQuery):
        parts = callback_query.data.split("_")
        format_type = parts[2]
        survey_id = parts[3]
        survey = storage.get_survey(survey_id)
        if not survey:
            await callback_query.answer("Опрос не найден")
            return
        if format_type == "csv":
            await self.export_csv(callback_query, survey)
        elif format_type == "json":
            await self.export_json(callback_query, survey)
        elif format_type == "text":
            await self.export_text(callback_query, survey)
        elif format_type == "excel":
            await self.export_excel(callback_query, survey)
        else:
            await callback_query.answer("Неподдерживаемый формат")

    async def export_csv(self, callback_query: types.CallbackQuery, survey):
        output = io.StringIO()
        writer = csv.writer(output)
        header = ["Вопрос", "ID пользователя", "Ответ", "Время"]
        writer.writerow(header)
        for response in survey.get("responses", []):
            question_id = response.get("question_id")
            question = next((q for q in survey.get("questions", []) if q.get("id") == question_id), {})
            question_text = question.get("text", "Неизвестный вопрос")
            answer = response.get("answer", "")
            if question.get("type") == "single_choice" and isinstance(answer, int):
                options = question.get("options", [])
                if 0 <= answer < len(options):
                    answer = options[answer]
            elif question.get("type") == "multiple_choice" and isinstance(answer, list):
                options = question.get("options", [])
                answer = ", ".join([options[i] for i in answer if 0 <= i < len(options)])
            writer.writerow([
                question_text,
                response.get("user_id", "Аноним"),
                answer,
                response.get("timestamp", "")
            ])
        csv_data = output.getvalue()
        output.close()
        bio = io.BytesIO(csv_data.encode("utf-8"))
        bio.name = f"survey_{survey.get('id', 'export')}_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
        await callback_query.message.answer_document(bio, caption=f"Экспорт опроса: {survey.get('title', 'Без названия')}")
        await callback_query.message.edit_text("✅ Экспорт в CSV успешно выполнен.")
        await callback_query.answer()

    async def export_excel(self, callback_query: types.CallbackQuery, survey):
        from utils.data_manager import save_to_excel

        responses = []
        for response in survey.get("responses", []):
            question_id = response.get("question_id")
            question = next((q for q in survey.get("questions", []) if q.get("id") == question_id), {})
            question_text = question.get("text", "Неизвестный вопрос")
            answer = response.get("answer", "")
            if question.get("type") == "single_choice" and isinstance(answer, int):
                options = question.get("options", [])
                if 0 <= answer < len(options):
                    answer = options[answer]
            elif question.get("type") == "multiple_choice" and isinstance(answer, list):
                options = question.get("options", [])
                answer = ", ".join([options[i] for i in answer if 0 <= i < len(options)])
            responses.append({"question": question_text, "answer": answer})

        filename = save_to_excel(
            "", "", "", "", "", "", "", responses, survey.get("title", "survey")
        )

        with open(filename, "rb") as f:
            bio = io.BytesIO(f.read())
        bio.name = os.path.basename(filename)
        await callback_query.message.answer_document(bio, caption=f"Экспорт опроса: {survey.get('title', 'Без названия')}")
        await callback_query.message.edit_text("✅ Экспорт в Excel успешно выполнен.")
        await callback_query.answer()

    async def export_json(self, callback_query: types.CallbackQuery, survey):
        export_data = {
            "id": survey.get("id"),
            "title": survey.get("title"),
            "description": survey.get("description", ""),
            "created_at": survey.get("created_at", ""),
            "status": survey.get("status", ""),
            "is_anonymous": survey.get("is_anonymous", False),
            "questions": survey.get("questions", []),
            "responses": survey.get("responses", [])
        }
        json_data = json.dumps(export_data, ensure_ascii=False, indent=2)
        bio = io.BytesIO(json_data.encode("utf-8"))
        bio.name = f"survey_{survey.get('id', 'export')}_{datetime.datetime.now().strftime('%Y%m%d')}.json"
        await callback_query.message.answer_document(bio, caption=f"Экспорт опроса: {survey.get('title', 'Без названия')}")
        await callback_query.message.edit_text("✅ Экспорт в JSON успешно выполнен.")
        await callback_query.answer()

    async def export_text(self, callback_query: types.CallbackQuery, survey):
        report = []
        report.append(f"ОТЧЕТ ПО ОПРОСУ: {survey.get('title', 'Без названия')}")
        report.append(f"ID: {survey.get('id', '')}")
        report.append(f"Описание: {survey.get('description', '')}")
        report.append(f"Создан: {survey.get('created_at', '')}")
        report.append(f"Статус: {survey.get('status', '')}")
        report.append(f"Анонимный: {'Да' if survey.get('is_anonymous', False) else 'Нет'}")
        report.append("")
        questions = {q.get("id"): q for q in survey.get("questions", [])}
        for question_id, question in questions.items():
            report.append(f"ВОПРОС: {question.get('text', '')}")
            report.append(f"Тип: {question.get('type', '')}")
            question_responses = [r for r in survey.get("responses", []) if r.get("question_id") == question_id]
            report.append(f"Всего ответов: {len(question_responses)}")
            report.append("")
            if question.get("type") == "single_choice":
                options = question.get("options", [])
                counts = [0] * len(options)
                other = 0
                for response in question_responses:
                    answer = response.get("answer")
                    if isinstance(answer, int) and 0 <= answer < len(options):
                        counts[answer] += 1
                    else:
                        other += 1
                total = sum(counts) + other
                for i, option in enumerate(options):
                    percentage = (counts[i] / total * 100) if total > 0 else 0
                    report.append(f"  {option}: {counts[i]} ({percentage:.1f}%)")
                if other:
                    percentage = (other / total * 100) if total > 0 else 0
                    report.append(f"  Другое: {other} ({percentage:.1f}%)")
            elif question.get("type") == "multiple_choice":
                options = question.get("options", [])
                counts = [0] * len(options)
                other = 0
                for response in question_responses:
                    answer = response.get("answer", [])
                    if isinstance(answer, list):
                        for option_index in answer:
                            if 0 <= option_index < len(options):
                                counts[option_index] += 1
                    else:
                        other += 1
                total = len(question_responses)
                for i, option in enumerate(options):
                    percentage = (counts[i] / total * 100) if total else 0
                    report.append(f"  {option}: {counts[i]} ({percentage:.1f}%)")
                if other:
                    percentage = (other / total * 100) if total else 0
                    report.append(f"  Другое: {other} ({percentage:.1f}%)")
            elif question.get("type") == "text_answer":
                report.append("Текстовые ответы:")
                for i, response in enumerate(question_responses):
                    answer = response.get("answer", "")
                    report.append(f"  {i+1}. {answer}")
            report.append("")
        report_text = "\n".join(report)
        bio = io.BytesIO(report_text.encode("utf-8"))
        bio.name = f"survey_{survey.get('id', 'export')}_{datetime.datetime.now().strftime('%Y%m%d')}.txt"
        await callback_query.message.answer_document(bio, caption=f"Текстовый отчет по опросу: {survey.get('title', 'Без названия')}")
        await callback_query.message.edit_text("✅ Текстовый отчет успешно создан.")
        await callback_query.answer()

    def on_plugin_load(self):
        logger.info("Плагин экспорта загружен")

    def on_plugin_unload(self):
        logger.info("Плагин экспорта выгружен")

def load_plugin():
    return ExportPlugin()
