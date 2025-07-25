"""Access control plugin skeleton."""

from aiogram import Router, types

__plugin_meta__ = {
    "admin_menu": [],
    "commands": [],
    "permissions": [],
}


class AccessControlPlugin:
    """Placeholder access control plugin."""

    def __init__(self):
        self.name = "access_control_plugin"

    async def register_handlers(self, router: Router):
        """Register plugin handlers."""
        pass

    def get_commands(self):
        """Return bot commands defined in meta-data."""
        meta = getattr(self, "__plugin_meta__", None)
        try:
            BotCommandCls = types.BotCommand
        except AttributeError:  # pragma: no cover - fallback for tests
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
    return AccessControlPlugin()
