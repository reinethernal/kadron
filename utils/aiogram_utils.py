from aiogram import Router, Bot
import logging


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


logger = logging.getLogger(__name__)


async def try_pin_message(bot: Bot, chat_id: int, message_id: int) -> None:
    """Attempt to pin a message if the bot has permission."""
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id, me.id)
        can_pin = getattr(member, "can_pin_messages", False) or member.status == "creator"
        if can_pin:
            await bot.pin_chat_message(
                chat_id=chat_id, message_id=message_id, disable_notification=False
            )
        else:
            logger.warning(f"У бота нет прав закреплять сообщения в чате {chat_id}")
    except Exception as e:
        logger.error(f"Не удалось закрепить сообщение в чате {chat_id}: {e}")
