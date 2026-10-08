from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.session import Database
from app.services.admins import get_admin
from sqlalchemy import select
from app.database.models import Admin
from app.states.user import UserStates
from app.keyboards.reply import help_keyboard
from app.utils.ui import require_subscription

router = Router(name="user_help")


@router.message(F.text == "ℹ️ YORDAM")
async def help_home(message: Message, state: FSMContext, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    await state.clear()
    await message.answer("ℹ️ YORDAM\n\nKerakli bo‘limni tanlang.", reply_markup=help_keyboard())


@router.message(F.text == "📖 BOT HAQIDA")
async def about(message: Message, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    await message.answer("📚 KITOBXONLAR BOTI\n\nKitoblarni topish, kanalimizdagi ma’lumotlarga o‘tish va kitob bo‘yicha test ishlash uchun yaratilgan.")


@router.message(F.text == "❓ QANDAY ISHLAYDI")
async def how(message: Message, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    await message.answer("1. 📚 Kitobni qidiring.\n2. 📖 Batafsil ma’lumotni oching.\n3. 🧠 Test ishlang.\n4. 🏆 Natijangizni TOP va profil orqali kuzating.")


@router.message(F.text == "💬 ADMIN BILAN BOG‘LANISH")
async def contact_admin(message: Message, state: FSMContext, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    await state.set_state(UserStates.contact_admin)
    await message.answer("💬 Xabaringizni yozing. U faol adminlarga yuboriladi.")


@router.message(UserStates.contact_admin)
async def contact_message(message: Message, state: FSMContext, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    async with db.session() as session:
        result = await session.execute(select(Admin.telegram_id).where(Admin.is_active.is_(True)))
        admin_ids = [int(x) for x in result.scalars().all()]
    text = (message.text or "").strip()
    if not text:
        await message.answer("Matnli xabar yuboring.")
        return
    user_line = f"💬 FOYDALANUVCHI XABARI\n\n🆔 {message.from_user.id}\n👤 @{message.from_user.username or 'username_yok'}\n\n{text}"
    sent = 0
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, user_line)
            sent += 1
        except Exception:
            pass
    await state.clear()
    await message.answer("✅ Xabaringiz adminlarga yuborildi." if sent else "⚠️ Hozircha faol admin topilmadi.")


@router.message(Command("help"))
async def help_command(message: Message, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    await message.answer("ℹ️ YORDAM\n\nKerakli bo‘limni tanlang.", reply_markup=help_keyboard())


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext, db: Database, bot) -> None:
    await state.clear()
    if await require_subscription(message, bot, db):
        await message.answer("✅ Joriy amal bekor qilindi.")
