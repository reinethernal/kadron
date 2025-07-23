"""
Плагин шаблонов опросов.

Позволяет сохранять существующие опросы как шаблоны, просматривать список
шаблонов, удалять их и создавать новые опросы на основе выбранного шаблона.
"""

from aiogram import Router, types
from aiogram.filters import Command
from datetime import datetime
import uuid
import logging
from utils import remove_plugin_handlers
from plugins_admin.storage_plugin import storage

logger = logging.getLogger(__name__)

__plugin_meta__ = {
    "admin_menu": [],
    "commands": [],
    "permissions": [],
}


class SurveyTemplatesPlugin:
    """Управление шаблонами опросов"""

    def __init__(self):
        self.name = "survey_templates_plugin"
        self.description = "Шаблоны опросов"

    async def register_handlers(self, router: Router):
        router.message.register(self.cmd_save_template, Command("save_template"))
        router.message.register(self.cmd_list_templates, Command("list_templates"))
        router.message.register(self.cmd_delete_template, Command("delete_template"))
        router.message.register(self.cmd_use_template, Command("use_template"))

    async def unregister_handlers(self, router: Router):
        remove_plugin_handlers(self, router)

    def get_commands(self):
        return []

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
