from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.session import Database
from app.keyboards.reply import books_keyboard, help_keyboard, main_keyboard, profile_keyboard, quiz_keyboard
from app.services.admins import is_admin
from app.utils.ui import menu_text, require_subscription

router = Router(name="user_navigation")


@router.message(F.text == "⬅️ ASOSIY MENYU")
async def main_menu(message: Message, state: FSMContext, db: Database, bot) -> None:
    await state.clear()
    if not await require_subscription(message, bot, db):
        return
    async with db.session() as session:
        admin = await is_admin(session, message.from_user.id)
    await message.answer(menu_text(), reply_markup=main_keyboard(admin))


@router.message(F.text == "⬅️ KITOBLAR")
async def back_books(message: Message, state: FSMContext, db: Database, bot) -> None:
    await state.clear()
    if not await require_subscription(message, bot, db):
        return
    await message.answer("📚 KITOBLAR\n\nKitobni toping va uning kanal ma’lumotlariga o‘ting.", reply_markup=books_keyboard())


@router.message(F.text == "⬅️ TESTLAR")
async def back_tests(message: Message, state: FSMContext, db: Database, bot) -> None:
    await state.clear()
    if not await require_subscription(message, bot, db):
        return
    await message.answer("🧠 TEST\n\nBilimingizni sinash uchun rejimni tanlang.", reply_markup=quiz_keyboard())


@router.message(F.text == "⬅️ PROFIL")
async def back_profile(message: Message, state: FSMContext, db: Database, bot) -> None:
    await state.clear()
    if not await require_subscription(message, bot, db):
        return
    await message.answer("👤 PROFIL\n\nShaxsiy natijalaringiz shu yerda.", reply_markup=profile_keyboard())


@router.message(F.text == "⬅️ YORDAM")
async def back_help(message: Message, state: FSMContext, db: Database, bot) -> None:
    await state.clear()
    if not await require_subscription(message, bot, db):
        return
    await message.answer("ℹ️ YORDAM\n\nKerakli bo‘limni tanlang.", reply_markup=help_keyboard())
