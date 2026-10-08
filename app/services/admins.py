from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models import Admin
from app.constants import ROLE_ADMIN, ROLE_MODERATOR, ROLE_SUPERADMIN


async def ensure_super_admins(session: AsyncSession, settings: Settings) -> None:
    for telegram_id in settings.super_admin_ids:
        result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
        row = result.scalar_one_or_none()
        if row is None:
            session.add(Admin(telegram_id=telegram_id, role=ROLE_SUPERADMIN, is_active=True))
        else:
            row.role = ROLE_SUPERADMIN
            row.is_active = True
    await session.commit()


async def get_admin(session: AsyncSession, telegram_id: int) -> Admin | None:
    result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id, Admin.is_active.is_(True)))
    return result.scalar_one_or_none()


async def is_admin(session: AsyncSession, telegram_id: int) -> bool:
    return await get_admin(session, telegram_id) is not None


async def is_superadmin(session: AsyncSession, telegram_id: int) -> bool:
    admin = await get_admin(session, telegram_id)
    return bool(admin and admin.role == ROLE_SUPERADMIN)


async def add_admin(session: AsyncSession, telegram_id: int, role: str) -> None:
    if role not in {ROLE_ADMIN, ROLE_MODERATOR, ROLE_SUPERADMIN}:
        raise ValueError("Noto‘g‘ri admin roli")
    result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
    row = result.scalar_one_or_none()
    if row is None:
        session.add(Admin(telegram_id=telegram_id, role=role, is_active=True))
    else:
        row.role = role
        row.is_active = True
    await session.commit()


async def remove_admin(session: AsyncSession, telegram_id: int) -> None:
    result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
    row = result.scalar_one_or_none()
    if row:
        row.is_active = False
        await session.commit()
