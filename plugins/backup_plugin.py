"""Backup plugin skeleton."""

from aiogram import Router


class BackupPlugin:
    """Placeholder backup plugin."""

    def __init__(self):
        self.name = "backup_plugin"

    async def register_handlers(self, router: Router):
        """Register plugin handlers."""
        pass


def load_plugin():
    """Return plugin instance."""
    return BackupPlugin()
