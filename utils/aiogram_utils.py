from aiogram import Router


def remove_plugin_handlers(plugin, router: Router) -> None:
    """Remove all handlers registered by a plugin from the router."""
    for attr in dir(router):
        event = getattr(router, attr)
        handlers = getattr(event, "handlers", None)
        if handlers is None:
            continue
        handlers[:] = [
            h
            for h in handlers
            if getattr(getattr(h, "callback", h), "__self__", None) is not plugin
        ]
