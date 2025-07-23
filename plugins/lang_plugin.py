"""Language support plugin skeleton."""

from aiogram import Router


class LangPlugin:
    """Placeholder language plugin."""

    def __init__(self):
        self.name = "lang_plugin"

    async def register_handlers(self, router: Router):
        """Register plugin handlers."""
        pass


def load_plugin():
    """Return plugin instance."""
    return LangPlugin()
