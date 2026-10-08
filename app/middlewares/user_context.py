from __future__ import annotations

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.database.session import Database
from app.config import Settings
from app.services.users import get_or_create_user


class UserContextMiddleware(BaseMiddleware):
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = getattr(event, "from_user", None)
        if user:
            async with self.db.session() as session:
                db_user = await get_or_create_user(session, user)
                if db_user.is_blocked:
                    return None
                data["db_user"] = db_user
        data["db"] = self.db
        data["settings"] = self.settings
        return await handler(event, data)
