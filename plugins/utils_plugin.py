"""Utilities plugin skeleton."""

from aiogram import Router


class UtilsPlugin:
    """Placeholder utilities plugin."""

    def __init__(self):
        self.name = "utils_plugin"

    async def register_handlers(self, router: Router):
        """Register plugin handlers."""
        pass


def load_plugin():
    """Return plugin instance."""
    return UtilsPlugin()
