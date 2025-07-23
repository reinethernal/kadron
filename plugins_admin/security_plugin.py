"""Security plugin skeleton."""

from aiogram import Router

__plugin_meta__ = {
    "admin_menu": [],
    "commands": [],
    "permissions": [],
}


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
