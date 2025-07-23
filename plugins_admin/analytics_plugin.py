"""Basic analytics plugin skeleton."""

from aiogram import Router


class AnalyticsPlugin:
    """Placeholder analytics plugin."""

    def __init__(self):
        self.name = "analytics_plugin"

    async def register_handlers(self, router: Router):
        """Register plugin handlers."""
        # Handlers would be registered here
        pass


def load_plugin():
    """Return plugin instance."""
    return AnalyticsPlugin()
