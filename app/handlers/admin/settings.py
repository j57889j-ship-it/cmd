from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from app.constants import ROLE_ADMIN, ROLE_MODERATOR, ROLE_SUPERADMIN
from app.database.models import Admin
from app.database.session import Database
from app.keyboards.reply import admin_settings_keyboard
from app.services.admins import add_admin, remove_admin
from app.states.admin import AdminAddAdminStates, AdminRemoveAdminStates
from app.utils.auth import is_super, require_admin

router = Router(name="admin_settings")


@router.message(F.text == "⚙️ SOZLAMALAR")
async def settings_home(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not is_super(role):
        return
    await message.answer("⚙️ SOZLAMALAR\n\nAdmin huquqlari shu bo‘limdan boshqariladi.", reply_markup=admin_settings_keyboard())


@router.message(F.text == "👑 ADMINLAR")
async def admins_list(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not is_super(role):
        return
    async with db.session() as session:
        result = await session.execute(select(Admin).where(Admin.is_active.is_(True)).order_by(Admin.id))
        admins = list(result.scalars().all())
    lines = ["👑 ADMINLAR", ""]
    for admin in admins:
        lines.append(f"🆔 {admin.telegram_id} — {admin.role}")
    lines.extend(["", "➕ Yangi admin qo‘shish uchun: ADMIN QO‘SHISH tugmasi"])
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ ADMIN QO‘SHISH")],
        [KeyboardButton(text="🗑 ADMIN O‘CHIRISH")],
        [KeyboardButton(text="⬅️ ADMIN PANEL")],
    ], resize_keyboard=True)
    await message.answer("\n".join(lines), reply_markup=keyboard)


@router.message(F.text == "➕ ADMIN QO‘SHISH")
async def add_admin_start(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not is_super(role):
        return
    await state.set_state(AdminAddAdminStates.telegram_id)
    await message.answer("🆔 Yangi adminning Telegram ID sini yuboring.")


@router.message(AdminAddAdminStates.telegram_id)
async def add_admin_id(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("Telegram ID raqam bo‘lishi kerak.")
        return
    await state.update_data(telegram_id=int(message.text))
    await state.set_state(AdminAddAdminStates.role)
    await message.answer("Rolni yuboring: admin yoki moderator")


@router.message(AdminAddAdminStates.role)
async def add_admin_role(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not is_super(role):
        return
    value = message.text.strip().lower()
    if value not in {ROLE_ADMIN, ROLE_MODERATOR}:
        await message.answer("Faqat admin yoki moderator.")
        return
    data = await state.get_data()
    async with db.session() as session:
        await add_admin(session, int(data["telegram_id"]), value)
    await state.clear()
    await message.answer("✅ Admin qo‘shildi.")


@router.message(F.text == "🗑 ADMIN O‘CHIRISH")
async def remove_admin_start(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not is_super(role):
        return
    await state.set_state(AdminRemoveAdminStates.telegram_id)
    await message.answer("🗑 O‘chiriladigan admin Telegram ID sini yuboring.")


@router.message(AdminRemoveAdminStates.telegram_id)
async def remove_admin_value(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not is_super(role):
        return
    telegram_id = int(message.text)
    async with db.session() as session:
        await remove_admin(session, telegram_id)
    await state.clear()
    await message.answer("✅ Admin o‘chirildi.")
