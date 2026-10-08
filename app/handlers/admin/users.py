from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import func, select

from app.database.models import QuizAnswer, QuizAttempt, User
from app.database.session import Database
from app.keyboards.reply import admin_users_keyboard
from app.services.users import search_users
from app.states.admin import AdminBroadcastStates, AdminUserStates
from app.utils.auth import can_manage_users, require_admin

router = Router(name="admin_users")


@router.message(F.text == "👥 FOYDALANUVCHILAR")
async def users_home(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_users(role):
        return
    await message.answer("👥 FOYDALANUVCHILAR", reply_markup=admin_users_keyboard())


async def _load_user(db: Database, query: str) -> User | None:
    async with db.session() as session:
        users = await search_users(session, query, limit=5)
        return users[0] if len(users) == 1 else None


@router.message(F.text == "🔎 USER QIDIRISH")
async def search_start(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_users(role):
        return
    await state.set_state(AdminUserStates.search)
    await message.answer("🔎 Username yoki Telegram ID yuboring.")


@router.message(AdminUserStates.search)
async def search_value(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_users(role):
        return
    async with db.session() as session:
        users = await search_users(session, message.text, limit=10)
    await state.clear()
    if not users:
        await message.answer("📭 User topilmadi.")
        return
    lines = ["👥 TOPILGAN USERLAR", ""]
    for user in users:
        name = f"@{user.username}" if user.username else user.first_name or str(user.telegram_id)
        lines.append(f"🆔 {user.telegram_id} — {name} — {user.score} ⭐")
    lines.append("\nBitta userni to‘liq boshqarish uchun aniq Telegram ID yuboring.")
    await message.answer("\n".join(lines))


@router.message(F.text == "📊 USER STATISTIKASI")
async def user_stats_start(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_users(role):
        return
    await state.set_state(AdminUserStates.manage)
    await message.answer("📊 User Telegram ID sini yuboring.")


@router.message(AdminUserStates.manage)
async def user_stats_value(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_users(role):
        return
    if not message.text.isdigit():
        await message.answer("Telegram ID raqam bo‘lishi kerak.")
        return
    async with db.session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == int(message.text)))
        if not user:
            await message.answer("User topilmadi.")
            return
        attempts = await session.scalar(select(func.count(QuizAttempt.id)).where(QuizAttempt.user_id == user.id)) or 0
    await state.clear()
    name = f"@{user.username}" if user.username else user.first_name or str(user.telegram_id)
    await message.answer(
        "👤 USER\n\n"
        f"{name}\n🆔 {user.telegram_id}\n"
        f"⭐ Ball: {user.score}\n"
        f"🧠 Testlar: {attempts}\n"
        f"✅ To‘g‘ri: {user.correct_answers}\n"
        f"❌ Xato: {user.wrong_answers}\n"
        f"🔥 Streak: {user.streak}\n"
        f"{'🚫 Bloklangan' if user.is_blocked else '🟢 Faol'}"
    )


@router.message(F.text == "🚫 BLOK / UNBLOK")
async def block_start(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_users(role):
        return
    await state.set_state(AdminUserStates.block)
    await message.answer("🚫 Telegram ID yuboring.")


@router.message(AdminUserStates.block)
async def block_value(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_users(role):
        return
    if not message.text.isdigit():
        await message.answer("Telegram ID raqam bo‘lishi kerak.")
        return
    async with db.session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == int(message.text)))
        if not user:
            await message.answer("User topilmadi.")
            return
        user.is_blocked = not user.is_blocked
        status = user.is_blocked
        await session.commit()
    await state.clear()
    await message.answer("✅ Bloklandi." if status else "✅ Blokdan chiqarildi.")


@router.message(F.text == "🧹 USER STATISTIKASINI TOZALASH")
async def clean_start(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_users(role):
        return
    await state.set_state(AdminUserStates.clean)
    await message.answer("🧹 Telegram ID yuboring. Ball va test statistikasi 0 ga qaytariladi.")


@router.message(AdminUserStates.clean)
async def clean_value(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_users(role):
        return
    if not message.text.isdigit():
        await message.answer("Telegram ID raqam bo‘lishi kerak.")
        return
    async with db.session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == int(message.text)))
        if not user:
            await message.answer("User topilmadi.")
            return
        user.score = 0
        user.total_questions = 0
        user.correct_answers = 0
        user.wrong_answers = 0
        user.streak = 0
        user.last_quiz_day = None
        await session.commit()
    await state.clear()
    await message.answer("✅ User statistikasi tozalandi.")


@router.message(F.text == "📣 XABAR YUBORISH")
async def broadcast_start(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_users(role):
        return
    await state.set_state(AdminBroadcastStates.text)
    await message.answer("📣 Barcha bloklanmagan userlarga yuboriladigan xabarni yuboring.\n\nBekor qilish: /cancel")


@router.message(AdminBroadcastStates.text)
async def broadcast_send(message: Message, state: FSMContext, db: Database, bot) -> None:
    role = await require_admin(message, db)
    if not can_manage_users(role):
        return
    async with db.session() as session:
        result = await session.execute(select(User.telegram_id).where(User.is_blocked.is_(False)))
        ids = [int(v) for v in result.scalars().all()]
    sent = 0
    failed = 0
    for telegram_id in ids:
        try:
            await bot.send_message(telegram_id, message.text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await state.clear()
    await message.answer(f"📣 Yuborish yakunlandi.\n\n✅ Yetkazildi: {sent}\n⚠️ Yetkazilmadi: {failed}")
