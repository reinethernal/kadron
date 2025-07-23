"""Notification plugin skeleton."""

from aiogram import Router

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


def load_plugin():
    """Return plugin instance."""
    return NotifyPlugin()
