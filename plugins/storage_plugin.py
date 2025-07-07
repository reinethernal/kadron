"""
Плагин для работы с постоянным хранилищем данных для Telegram-бота.
Реализует сохранение и загрузку состояния пользователей, данных опросов и настроек.
"""

import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Storage:
    """Класс для хранения постоянных данных"""

    def __init__(self, storage_file="bot_data.json"):
        self.storage_file = storage_file
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        """Загружает данные из файла хранилища"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error(
                    f"Не удалось разобрать {self.storage_file}, создаются новые данные"
                )
                return {"users": {}, "surveys": {}, "settings": {}}
        else:
            return {"users": {}, "surveys": {}, "settings": {}}

    def _save_data(self):
        """Сохраняет данные в файл хранилища"""
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_user_state(self, user_id: int) -> Dict:
        """Получает состояние пользователя по его ID"""
        user_id = str(user_id)  # Преобразуем в строку для JSON
        if "users" not in self.data:
            self.data["users"] = {}
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {}
        return self.data["users"][user_id]

    def set_user_state(self, user_id: int, key: str, value: Any):
        """Устанавливает значение состояния пользователя по ключу"""
        user_id = str(user_id)
        if "users" not in self.data:
            self.data["users"] = {}
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {}
        self.data["users"][user_id][key] = value
        self._save_data()

    def reset_user_state(self, user_id: int):
        """Сбрасывает состояние пользователя"""
        user_id = str(user_id)
        if "users" in self.data and user_id in self.data["users"]:
            self.data["users"][user_id] = {}
            self._save_data()

    def get_survey(self, survey_id: str) -> Optional[Dict]:
        """Получает опрос по его ID"""
        if "surveys" not in self.data:
            self.data["surveys"] = {}
        return self.data["surveys"].get(survey_id)

    def save_survey(self, survey_id: str, survey_data: Dict):
        """Сохраняет данные опроса"""
        if "surveys" not in self.data:
            self.data["surveys"] = {}
        self.data["surveys"][survey_id] = survey_data
        self._save_data()

    def delete_survey(self, survey_id: str):
        """Удаляет опрос по его ID"""
        if "surveys" in self.data and survey_id in self.data["surveys"]:
            del self.data["surveys"][survey_id]
            self._save_data()

    def get_all_surveys(self) -> Dict:
        """Возвращает все опросы"""
        if "surveys" not in self.data:
            self.data["surveys"] = {}
        return self.data["surveys"]

    def get_setting(self, key: str, default=None) -> Any:
        """Получает настройку по ключу"""
        if "settings" not in self.data:
            self.data["settings"] = {}
        return self.data["settings"].get(key, default)

    def set_setting(self, key: str, value: Any):
        """Устанавливает значение настройки"""
        if "settings" not in self.data:
            self.data["settings"] = {}
        self.data["settings"][key] = value
        self._save_data()


# Создаём глобальный экземпляр хранилища
storage = Storage()


class StoragePlugin:
    """Плагин для обеспечения функциональности постоянного хранилища"""

    def __init__(self):
        self.name = "storage_plugin"
        self.description = "Обеспечивает постоянное хранилище данных"

    async def register_handlers(self, dp):
        """Обработчиков для этого плагина нет"""
        pass

    def get_commands(self):
        """Команды для этого плагина отсутствуют"""
        return []

    def on_plugin_load(self):
        """Вызывается при загрузке плагина"""
        logger.info(
            f"Плагин хранения данных загружен, файл данных: {storage.storage_file}"
        )

    def on_plugin_unload(self):
        """Вызывается при выгрузке плагина"""
        storage._save_data()
        logger.info("Плагин хранения данных выгружен, данные сохранены")


def load_plugin():
    """Загружает плагин"""
    return StoragePlugin()
