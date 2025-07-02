# Kadron Bot

A Telegram bot for managing polls and group interactions. The project is built with [aiogram](https://github.com/aiogram/aiogram) and uses a plugin architecture for additional features.

## Prerequisites

- Python 3.10 or newer
- `pip` for installing dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

## Environment variables

Copy `example.env` to `.env` and fill in your values:

```bash
cp example.env .env
```

The variables are:

| Name | Description |
| --- | --- |
| `BOT_TOKEN` | Token obtained from BotFather |
| `DATABASE` | Path to the SQLite database file |
| `ADMIN_IDS` | Comma separated Telegram user IDs with admin access |
| `ENABLE_LOGGING` | Enable additional logging (`True` or `False`) |
| `LOGGING_LEVEL` | Logging level (e.g. `DEBUG` or `INFO`) |
| `ENABLE_CAPTCHA` | Use captcha for new group members |
| `CAPTCHA_TIMEOUT` | Captcha timeout in minutes |
| `MAX_WARNINGS` | Maximum number of warnings before action |
| `INACTIVITY_DAYS` | Days of inactivity before removal |
| `WELCOME_MESSAGE` | Default welcome text for new users |

## Running the bot

After configuring `.env` run:

```bash
python main.py
```

Use the correct Python executable if you have multiple versions installed (e.g. `python3.10 main.py`).

## Plugins

Plugins live in the `plugins` directory. `plugin_manager.py` automatically loads every file that ends with `_plugin.py`.

For a walkthrough on creating your own plugin using `plugin_template.py` see
[CONTRIBUTING.md](CONTRIBUTING.md).

Example usage:

```python
from aiogram import Dispatcher
from plugin_manager import PluginManager

# dp is your Dispatcher instance
pm = PluginManager(dp)
await pm.load_plugins()
await pm.setup_bot_commands(bot)
```

To disable a plugin either rename or remove its file or call `unload_plugin` at runtime:

```python
await pm.unload_plugin('test_mode_plugin')  # name without .py
```

Load it again with `load_plugin('test_mode_plugin')`.

## Example run

```bash
python main.py
```

