from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import func, select

from app.database.models import Book, Question, QuizAttempt, User
from app.database.session import Database
from app.keyboards.reply import admin_keyboard
from app.utils.auth import require_admin

router = Router(name="admin_dashboard")


@router.message(F.text == "🛠 ADMIN")
async def admin_home(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not role:
        return
    async with db.session() as session:
        users = await session.scalar(select(func.count(User.id))) or 0
        books = await session.scalar(select(func.count(Book.id)).where(Book.is_active.is_(True))) or 0
        questions = await session.scalar(select(func.count(Question.id)).where(Question.is_active.is_(True))) or 0
        tests = await session.scalar(select(func.count(QuizAttempt.id))) or 0
    await message.answer(
        "🛠 ADMIN PANEL\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"📚 Kitoblar: {books}\n"
        f"❓ Savollar: {questions}\n"
        f"🧠 Testlar: {tests}\n\n"
        "Kerakli boshqaruv markazini tanlang.",
        reply_markup=admin_keyboard(),
    )
