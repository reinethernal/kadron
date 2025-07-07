"""
Плагин шаблонов опросов.

Позволяет сохранять существующие опросы как шаблоны, просматривать список
шаблонов, удалять их и создавать новые опросы на основе выбранного шаблона.
"""

from aiogram import Dispatcher, types
from aiogram.filters import Command
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

# Используем хранилище из storage_plugin
try:
    from .storage_plugin import storage
except Exception:

    class DummyStorage:
        def __init__(self):
            self.data = {}

        def get_survey(self, sid):
            return None

        def save_survey(self, sid, data):
            pass

        def _save_data(self):
            pass

    storage = DummyStorage()


class SurveyTemplatesPlugin:
    """Управление шаблонами опросов"""

    def __init__(self):
        self.name = "survey_templates_plugin"
        self.description = "Шаблоны опросов"

    async def register_handlers(self, dp: Dispatcher):
        dp.message.register(self.cmd_save_template, Command("save_template"))
        dp.message.register(self.cmd_list_templates, Command("list_templates"))
        dp.message.register(self.cmd_delete_template, Command("delete_template"))
        dp.message.register(self.cmd_use_template, Command("use_template"))

    def get_commands(self):
        return [
            types.BotCommand(
                command="save_template", description="Создать шаблон из опроса"
            ),
            types.BotCommand(command="list_templates", description="Список шаблонов"),
            types.BotCommand(command="delete_template", description="Удалить шаблон"),
            types.BotCommand(
                command="use_template", description="Новый опрос из шаблона"
            ),
        ]

    def _get_templates(self):
        return storage.data.setdefault("templates", {})

    async def cmd_save_template(self, message: types.Message):
        logger.debug(f"{message.text} from {message.from_user.id}")
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer(
                "Использование: /save_template <survey_id> <template_name>"
            )
            return
        survey_id, name = parts[1], parts[2]
        survey = storage.get_survey(survey_id)
        if not survey:
            await message.answer("Опрос не найден")
            return
        tpl_data = {
            "title": survey.get("title"),
            "description": survey.get("description"),
            "questions": survey.get("questions", []),
            "is_anonymous": survey.get("is_anonymous", False),
            "deadline": survey.get("deadline"),
        }
        templates = self._get_templates()
        templates[name] = tpl_data
        storage._save_data()
        await message.answer(f"Шаблон '{name}' сохранён")

    async def cmd_list_templates(self, message: types.Message):
        logger.debug(f"{message.text} from {message.from_user.id}")
        templates = self._get_templates()
        if not templates:
            await message.answer("Шаблоны отсутствуют")
            return
        text = "Доступные шаблоны:\n" + "\n".join(f"- {n}" for n in templates)
        await message.answer(text)

    async def cmd_delete_template(self, message: types.Message):
        logger.debug(f"{message.text} from {message.from_user.id}")
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Использование: /delete_template <template_name>")
            return
        name = parts[1]
        templates = self._get_templates()
        if name in templates:
            del templates[name]
            storage._save_data()
            await message.answer(f"Шаблон '{name}' удалён")
        else:
            await message.answer("Шаблон не найден")

    async def cmd_use_template(self, message: types.Message):
        logger.debug(f"{message.text} from {message.from_user.id}")
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer(
                "Использование: /use_template <template_name> <new_survey_title>"
            )
            return
        name, new_title = parts[1], parts[2]
        templates = self._get_templates()
        tpl = templates.get(name)
        if not tpl:
            await message.answer("Шаблон не найден")
            return
        survey_id = str(uuid.uuid4())
        survey = {
            "id": survey_id,
            "title": new_title,
            "description": tpl.get("description", ""),
            "creator_id": message.from_user.id,
            "created_at": datetime.now().isoformat(),
            "deadline": tpl.get("deadline", datetime.now().isoformat()),
            "is_anonymous": tpl.get("is_anonymous", False),
            "questions": tpl.get("questions", []),
            "responses": [],
            "status": "active",
        }
        storage.save_survey(survey_id, survey)
        await message.answer(f"Опрос '{new_title}' создан из шаблона '{name}'")


def load_plugin():
    """Загружает плагин"""
    return SurveyTemplatesPlugin()
