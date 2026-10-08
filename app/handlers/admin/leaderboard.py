from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import update

from app.database.models import User
from app.database.session import Database
from app.keyboards.reply import admin_leaderboard_keyboard
from app.services.quizzes import top_users
from app.services.settings import get_setting, set_setting
from app.states.admin import AdminSettingStates
from app.utils.auth import require_admin, can_manage_users, is_super

router = Router(name="admin_leaderboard")


@router.message(F.text == "🏆 REYTING")
async def leaderboard_home(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not role:
        return
    await message.answer("🏆 REYTING\n\nBu yerda faqat umumiy TOP kitobxonlar boshqariladi.", reply_markup=admin_leaderboard_keyboard())


@router.message(F.text == "👑 TOP KITOBXONLAR")
async def top_view(message: Message, db: Database, settings) -> None:
    role = await require_admin(message, db)
    if not role:
        return
    async with db.session() as session:
        users = await top_users(session, settings.top_limit)
    lines = ["👑 TOP KITOBXONLAR", ""]
    for i, user in enumerate(users, 1):
        name = f"@{user.username}" if user.username else user.first_name or str(user.telegram_id)
        lines.append(f"{i}. {name} — {user.score} ⭐")
    await message.answer("\n".join(lines) if len(lines) > 2 else "📭 Hali TOP mavjud emas.")


@router.message(F.text == "⚙️ TOP SOZLAMALARI")
async def top_settings(message: Message, state: FSMContext, db: Database, settings) -> None:
    role = await require_admin(message, db)
    if not is_super(role):
        return
    async with db.session() as session:
        enabled = await get_setting(session, "top_enabled", "1")
        limit = await get_setting(session, "top_limit", str(settings.top_limit))
    await state.clear()
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢/🔴 TOP ON/OFF", callback_data="top:toggle")],
        [InlineKeyboardButton(text="🔢 LIMIT", callback_data="top:limit")],
    ])
    await message.answer(f"🏆 TOP SOZLAMALARI\n\nHolat: {'🟢 ON' if enabled == '1' else '🔴 OFF'}\nKo‘rsatiladiganlar: {limit}", reply_markup=kb)


@router.callback_query(lambda c: c.data == "top:toggle")
async def toggle_top(callback: CallbackQuery, db: Database) -> None:
    role = await require_admin(callback, db)
    if not is_super(role):
        await callback.answer()
        return
    async with db.session() as session:
        value = await get_setting(session, "top_enabled", "1")
        await set_setting(session, "top_enabled", "0" if value == "1" else "1")
    await callback.answer("TOP holati yangilandi")


@router.callback_query(lambda c: c.data == "top:limit")
async def top_limit(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    role = await require_admin(callback, db)
    if not is_super(role):
        await callback.answer()
        return
    await state.set_state(AdminSettingStates.top_limit)
    await callback.answer()
    await callback.message.answer("🔢 TOPda nechta user ko‘rinsin? 5–50 oralig‘ida son yuboring.")


@router.message(AdminSettingStates.top_limit)
async def top_limit_value(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not is_super(role):
        return
    if not message.text.isdigit() or not 5 <= int(message.text) <= 50:
        await message.answer("5–50 oralig‘ida son yuboring.")
        return
    async with db.session() as session:
        await set_setting(session, "top_limit", message.text)
    await state.clear()
    await message.answer("✅ TOP limiti yangilandi. Environmentdagi default keyingi restartda ishlaydi; DB qiymati ustun.")


@router.message(F.text == "🧹 TOP RESET")
async def top_reset(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not is_super(role):
        return
    async with db.session() as session:
        await session.execute(update(User).values(score=0))
        await session.commit()
    await message.answer("✅ Barcha userlarning TOP bali 0 ga qaytarildi.")
