"""Access control plugin skeleton."""

from aiogram import Router


class AccessControlPlugin:
    """Placeholder access control plugin."""

    def __init__(self):
        self.name = "access_control_plugin"

    async def register_handlers(self, router: Router):
        """Register plugin handlers."""
        pass


def load_plugin():
    """Return plugin instance."""
    return AccessControlPlugin()
