"""Help plugin skeleton."""

from aiogram import Router


class HelpPlugin:
    """Placeholder help plugin."""

    def __init__(self):
        self.name = "help_plugin"

    async def register_handlers(self, router: Router):
        """Register plugin handlers."""
        pass


def load_plugin():
    """Return plugin instance."""
    return HelpPlugin()
