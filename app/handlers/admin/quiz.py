from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select, update, delete

from app.database.models import QuizAnswer, QuizAttempt, User, Question
from app.database.session import Database
from app.keyboards.reply import admin_quiz_keyboard
from app.services.settings import get_setting, set_setting
from app.states.admin import AdminSettingStates
from app.utils.auth import require_admin, is_super

router = Router(name="admin_quiz")


@router.message(F.text == "🧠 TEST BOSHQARUVI")
async def quiz_home(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not role:
        return
    await message.answer("🧠 TEST BOSHQARUVI", reply_markup=admin_quiz_keyboard())


@router.message(F.text == "⚙️ TEST SOZLAMALARI")
async def quiz_settings(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not is_super(role):
        return
    from app.config import get_settings
    cfg = get_settings()
    async with db.session() as session:
        points = await get_setting(session, "points_per_correct", str(cfg.points_per_correct))
        daily = await get_setting(session, "daily_question_id", "-")
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ BALL", callback_data="quizset:points")],
        [InlineKeyboardButton(text="📅 DAILY SAVOL", callback_data="quizset:daily")],
    ])
    await message.answer(f"⚙️ TEST SOZLAMALARI\n\n⭐ To‘g‘ri javob: {points} ball\n📅 Daily savol ID: {daily}", reply_markup=kb)


@router.callback_query(lambda c: c.data == "quizset:points")
async def quiz_points(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    role = await require_admin(callback, db)
    if not is_super(role):
        await callback.answer()
        return
    await state.set_state(AdminSettingStates.points)
    await callback.answer()
    await callback.message.answer("⭐ To‘g‘ri javob uchun nechta ball? 1–1000.")


@router.message(AdminSettingStates.points)
async def quiz_points_value(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not is_super(role):
        return
    if not message.text.isdigit() or not 1 <= int(message.text) <= 1000:
        await message.answer("1–1000 oralig‘ida son yuboring.")
        return
    async with db.session() as session:
        await set_setting(session, "points_per_correct", message.text)
    await state.clear()
    await message.answer("✅ Ball sozlamasi saqlandi.")


@router.callback_query(lambda c: c.data == "quizset:daily")
async def quiz_daily(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    role = await require_admin(callback, db)
    if not is_super(role):
        await callback.answer()
        return
    await state.set_state(AdminSettingStates.daily_question)
    await callback.answer()
    await callback.message.answer("📅 Savol ID sini yuboring. Daily savolni o‘chirish uchun 0 yozing.")


@router.message(AdminSettingStates.daily_question)
async def daily_value(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not is_super(role):
        return
    value = message.text.strip()
    if value != "0":
        async with db.session() as session:
            q = await session.get(Question, int(value))
            if not q:
                await message.answer("Bunday savol topilmadi.")
                return
    async with db.session() as session:
        await set_setting(session, "daily_question_id", "" if value == "0" else value)
    await state.clear()
    await message.answer("✅ Daily savol yangilandi.")


@router.message(F.text == "📊 TEST STATISTIKASI")
async def quiz_stats(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not role:
        return
    async with db.session() as session:
        attempts = await session.scalar(select(func.count(QuizAttempt.id))) or 0
        answers = await session.scalar(select(func.count(QuizAnswer.id))) or 0
        correct = await session.scalar(select(func.count(QuizAnswer.id)).where(QuizAnswer.is_correct.is_(True))) or 0
        users = await session.scalar(select(func.count(User.id))) or 0
    await message.answer(f"📊 TEST STATISTIKASI\n\n👥 User: {users}\n🧠 Testlar: {attempts}\n📝 Javoblar: {answers}\n✅ To‘g‘ri: {correct}\n❌ Xato: {answers - correct}")


@router.message(F.text == "🧹 NATIJALARNI TOZALASH")
async def clear_results(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not is_super(role):
        return
    async with db.session() as session:
        await session.execute(delete(QuizAnswer))
        await session.execute(delete(QuizAttempt))
        await session.execute(update(User).values(total_questions=0, correct_answers=0, wrong_answers=0, score=0, streak=0, last_quiz_day=None))
        await session.commit()
    await message.answer("✅ Test natijalari tozalandi.")
