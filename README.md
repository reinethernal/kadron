# Kadron Bot

Телеграм-бот для управления опросами и взаимодействия в группах. Проект построен на [aiogram](https://github.com/aiogram/aiogram) и использует архитектуру плагинов для расширения функциональности.

## Требования

- Python 3.10 или новее
- `pip` для установки зависимостей

Установите необходимые пакеты:

```bash
pip install -r requirements.txt
```

## Переменные окружения

Скопируйте `example.env` в `.env` и укажите свои значения:

```bash
cp example.env .env
```

Переменные:

| Имя | Описание |
| --- | --- |
| `BOT_TOKEN` | Токен, полученный от BotFather |
| `DATABASE` | Путь к файлу базы SQLite |
| `ADMIN_IDS` | ID администраторов Telegram через запятую. Допустимы формы `123,456` и `[123,456]` |
| `ENABLE_LOGGING` | Включить дополнительное логирование (`True` или `False`) |
| `LOGGING_LEVEL` | Уровень логирования (например, `DEBUG` или `INFO`) |
| `ENABLE_CAPTCHA` | Использовать капчу для новых участников групп |
| `CAPTCHA_TIMEOUT` | Время ожидания капчи в минутах |
| `MAX_WARNINGS` | Максимальное число предупреждений перед действием |
| `INACTIVITY_DAYS` | Количество дней неактивности до удаления |
| `WELCOME_MESSAGE` | Приветственное сообщение по умолчанию |

## Запуск бота

После настройки `.env` запустите:

```bash
python main.py
```

## Запуск тестов

Сначала установите зависимости:

```bash
pip install -r requirements.txt
```

Запустите тесты командой:

```bash
pytest
```

Тесты предполагают, что все пакеты из `requirements.txt` уже установлены.

Если установлено несколько версий Python, используйте соответствующий исполняемый файл (например, `python3.10 main.py`).

## Плагины

Плагины расположены в каталоге `plugins`. `plugin_manager.py` автоматически загружает каждый файл с окончанием `_plugin.py`.

Подробности создания собственных плагинов описаны в [CONTRIBUTING.md](CONTRIBUTING.md).

Пример использования:

```python
from aiogram import Dispatcher
from plugin_manager import PluginManager

# dp — экземпляр Dispatcher
pm = PluginManager(dp)
await pm.load_plugins()
await pm.setup_bot_commands(bot)
```

Чтобы отключить плагин, переименуйте или удалите его файл либо вызовите `unload_plugin` во время работы бота:

```python
await pm.unload_plugin('test_mode_plugin')  # имя без .py
```

Загрузить его снова можно вызовом `load_plugin('test_mode_plugin')`.

## Пример запуска

```bash
python main.py
```

## Экспорт опросов

Для получения файлов с результатами опросов используйте команду:

```bash
/export
```
