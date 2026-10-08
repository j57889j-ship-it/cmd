from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select, func

from app.database.models import User, QuizAttempt
from app.database.session import Database
from app.keyboards.reply import profile_keyboard
from app.services.quizzes import user_rank
from app.utils.ui import require_subscription

router = Router(name="user_profile")


@router.message(F.text == "👤 PROFIL")
async def profile(message: Message, state: FSMContext, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    await state.clear()
    async with db.session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        if not user:
            await message.answer("Profil topilmadi. /start ni bosing.")
            return
        rank = await user_rank(session, user.score)
    await message.answer(
        "👤 PROFIL\n\n"
        f"⭐ Ball: {user.score}\n"
        f"🧠 Testlar: {await _attempt_count(db, user.id)}\n"
        f"✅ To‘g‘ri: {user.correct_answers}\n"
        f"❌ Xato: {user.wrong_answers}\n"
        f"🔥 Streak: {user.streak} kun\n"
        f"🏆 TOP: #{rank}",
        reply_markup=profile_keyboard(),
    )


async def _attempt_count(db: Database, user_id: int) -> int:
    async with db.session() as session:
        value = await session.scalar(select(func.count(QuizAttempt.id)).where(QuizAttempt.user_id == user_id))
        return int(value or 0)


@router.message(F.text == "📊 STATISTIKA")
async def statistics(message: Message, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    async with db.session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        if not user:
            return
        rank = await user_rank(session, user.score)
        attempts = await session.scalar(select(func.count(QuizAttempt.id)).where(QuizAttempt.user_id == user.id))
    accuracy = round(user.correct_answers / user.total_questions * 100) if user.total_questions else 0
    await message.answer(
        "📊 STATISTIKA\n\n"
        f"⭐ Ball: {user.score}\n"
        f"🧠 Testlar: {int(attempts or 0)}\n"
        f"✅ To‘g‘ri: {user.correct_answers}\n"
        f"❌ Xato: {user.wrong_answers}\n"
        f"🎯 Aniqlik: {accuracy}%\n"
        f"🏆 O‘rin: #{rank}"
    )


@router.message(F.text.in_({"🔥 STREAK", "🔥 STREAKIM"}))
async def streak(message: Message, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    async with db.session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
    await message.answer(f"🔥 STREAK\n\nSizning ketma-ket kunlik streakingiz: {user.streak if user else 0} kun.")
