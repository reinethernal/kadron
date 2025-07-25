"""Notification plugin skeleton."""

from aiogram import Router, types

__plugin_meta__ = {
    "admin_menu": [],
    "commands": [],
    "permissions": [],
}


class NotifyPlugin:
    """Placeholder notification plugin."""

    def __init__(self):
        self.name = "notify_plugin"

    async def register_handlers(self, router: Router):
        """Register plugin handlers."""
        pass

    def get_commands(self):
        meta = getattr(self, "__plugin_meta__", None)
        try:
            BotCommandCls = types.BotCommand
        except AttributeError:  # pragma: no cover - tests may patch
            from aiogram.types import BotCommand as BotCommandCls
        if meta and isinstance(meta.get("commands"), list):
            return [
                BotCommandCls(
                    command=c.get("command"),
                    description=c.get("description", ""),
                )
                for c in meta["commands"]
                if isinstance(c, dict) and "command" in c
            ]
        return []


def load_plugin():
    """Return plugin instance."""
    return NotifyPlugin()
