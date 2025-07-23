"""Security plugin skeleton."""

from aiogram import Router


class SecurityPlugin:
    """Placeholder security plugin."""

    def __init__(self):
        self.name = "security_plugin"

    async def register_handlers(self, router: Router):
        """Register plugin handlers."""
        pass


def load_plugin():
    """Return plugin instance."""
    return SecurityPlugin()
