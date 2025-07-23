"""Security plugin providing optional 2FA and activity alerts."""

import asyncio
import logging
import os
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from aiogram import Router, types, Bot
from aiogram.filters import Command
try:
    from aiogram.exceptions import SkipHandler
except Exception:  # pragma: no cover - fallback for stubs
    class SkipHandler(Exception):
        """Fallback SkipHandler when aiogram provides none."""

        pass

from utils.env_utils import parse_admin_ids
from utils import remove_plugin_handlers

logger = logging.getLogger(__name__)

ENABLE_2FA = os.getenv("ENABLE_ADMIN_2FA", "False").lower() == "true"
CODE_TTL = int(os.getenv("ADMIN_2FA_TTL", "300"))
ALERT_THRESHOLD = int(os.getenv("LOGIN_ATTEMPT_THRESHOLD", "5"))
ALERT_WINDOW_MINUTES = int(os.getenv("LOGIN_ATTEMPT_WINDOW", "10"))
_hours = os.getenv("UNUSUAL_LOGIN_HOURS", "0-6").split("-")
try:
    UNUSUAL_HOUR_START, UNUSUAL_HOUR_END = int(_hours[0]), int(_hours[1])
except (ValueError, IndexError):
    UNUSUAL_HOUR_START, UNUSUAL_HOUR_END = 0, 6

__plugin_meta__ = {
    "admin_menu": [],
    "commands": [],
    "permissions": [],
}


class SecurityPlugin:
    """Security features for administrators."""

    def __init__(self, bot: Bot):
        self.name = "security_plugin"
        self.bot = bot
        self.admin_ids = parse_admin_ids()
        self.pending_codes: Dict[int, Tuple[str, datetime]] = {}
        self.verified: Dict[int, datetime] = {}
        self.attempts: Dict[int, List[datetime]] = {}

    async def register_handlers(self, router: Router):
        """Register plugin handlers when 2FA is enabled."""
        if ENABLE_2FA:
            router.message.register(self.handle_admin_command, Command("admin"))
            router.message.register(self.verify_code, Command("verify"))

    async def unregister_handlers(self, router: Router):
        if ENABLE_2FA:
            remove_plugin_handlers(self, router)

    # --- Helper methods -------------------------------------------------
    def _generate_code(self) -> str:
        return "".join(random.choices(string.digits, k=5))

    def _is_verified(self, user_id: int) -> bool:
        exp = self.verified.get(user_id)
        if exp and exp > datetime.now():
            return True
        self.verified.pop(user_id, None)
        return False

    def _record_attempt(self, user_id: int) -> None:
        now = datetime.now()
        attempts = self.attempts.setdefault(user_id, [])
        attempts.append(now)
        window_start = now - timedelta(minutes=ALERT_WINDOW_MINUTES)
        self.attempts[user_id] = [t for t in attempts if t >= window_start]

        if len(self.attempts[user_id]) >= ALERT_THRESHOLD:
            text = f"\u26a0\ufe0f Suspicious login attempts from user {user_id}"
            for aid in self.admin_ids:
                if aid == user_id:
                    continue
                asyncio.create_task(self._send_alert(aid, text))

    async def _send_alert(self, admin_id: int, text: str) -> None:  # pragma: no cover - best effort
        try:
            await self.bot.send_message(admin_id, text)
        except Exception as e:
            logger.error(f"Failed to send alert to {admin_id}: {e}")

    async def _alert_unusual_time(self, user_id: int) -> None:
        now_hour = datetime.now().hour
        if UNUSUAL_HOUR_START <= UNUSUAL_HOUR_END:
            unusual = UNUSUAL_HOUR_START <= now_hour < UNUSUAL_HOUR_END
        else:
            unusual = now_hour >= UNUSUAL_HOUR_START or now_hour < UNUSUAL_HOUR_END
        if unusual:
            msg = f"\u26a0\ufe0f Admin {user_id} login at unusual time ({now_hour:02d}:00)"
            for aid in self.admin_ids:
                if aid != user_id:
                    asyncio.create_task(self._send_alert(aid, msg))

    # --- Handlers -------------------------------------------------------
    async def handle_admin_command(self, message: types.Message):
        user_id = message.from_user.id

        if user_id not in self.admin_ids:
            self._record_attempt(user_id)
            return

        if self._is_verified(user_id):
            return

        code = self._generate_code()
        self.pending_codes[user_id] = (code, datetime.now() + timedelta(seconds=CODE_TTL))
        await message.answer(
            f"\u26a0\ufe0f Two-factor code: {code}\nSend /verify <code> to proceed."
        )
        await self._alert_unusual_time(user_id)
        raise SkipHandler()

    async def verify_code(self, message: types.Message):
        user_id = message.from_user.id

        if user_id not in self.admin_ids:
            self._record_attempt(user_id)
            return

        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Usage: /verify <code>")
            return
        code = parts[1].strip()

        entry = self.pending_codes.get(user_id)
        if not entry:
            await message.answer("No active verification code. Use /admin to request one.")
            return
        real_code, expiry = entry
        if expiry < datetime.now():
            self.pending_codes.pop(user_id, None)
            await message.answer("Code expired. Use /admin to request a new one.")
            return
        if code != real_code:
            self._record_attempt(user_id)
            await message.answer("Incorrect code.")
            return

        self.verified[user_id] = datetime.now() + timedelta(minutes=5)
        self.pending_codes.pop(user_id, None)
        await message.answer("Two-factor authentication successful.")


def load_plugin(bot: Bot):
    """Return plugin instance."""
    return SecurityPlugin(bot)
