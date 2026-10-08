from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


async def get_or_create_user(session: AsyncSession, telegram_user) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name or "",
            last_name=telegram_user.last_name,
        )
        session.add(user)
    else:
        user.username = telegram_user.username
        user.first_name = telegram_user.first_name or ""
        user.last_name = telegram_user.last_name
        user.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return user


async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def search_users(session: AsyncSession, query: str, limit: int = 20) -> list[User]:
    q = query.strip().lstrip("@").lower()
    clauses = [func.lower(User.username).contains(q)] if q else []
    try:
        numeric = int(q)
        clauses.append(User.telegram_id == numeric)
    except ValueError:
        pass
    stmt = select(User).where(*clauses).order_by(desc(User.score)).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())
