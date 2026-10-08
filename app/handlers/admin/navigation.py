from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.session import Database
from app.keyboards.reply import (
    admin_channels_keyboard,
    admin_content_keyboard,
    admin_keyboard,
    admin_leaderboard_keyboard,
    admin_quiz_keyboard,
    admin_settings_keyboard,
    admin_users_keyboard,
)
from app.utils.auth import require_admin
from app.utils.ui import menu_text
from app.keyboards.reply import main_keyboard
from app.services.admins import is_admin

router = Router(name="admin_navigation")


async def _guard(message: Message | CallbackQuery, db: Database):
    return await require_admin(message, db)


@router.message(F.text == "⬅️ ADMIN PANEL")
async def back_admin(message: Message, state: FSMContext, db: Database) -> None:
    if not await _guard(message, db):
        return
    await state.clear()
    await message.answer("🛠 ADMIN PANEL\n\nBoshqaruv markazi.", reply_markup=admin_keyboard())


@router.message(F.text == "⬅️ KONTENT")
async def back_content(message: Message, state: FSMContext, db: Database) -> None:
    if not await _guard(message, db):
        return
    await state.clear()
    await message.answer("📚 KONTENT\n\nKitob va savollar shu yerda boshqariladi.", reply_markup=admin_content_keyboard())


@router.message(F.text == "⬅️ FOYDALANUVCHILAR")
async def back_users(message: Message, state: FSMContext, db: Database) -> None:
    if not await _guard(message, db):
        return
    await state.clear()
    await message.answer("👥 FOYDALANUVCHILAR", reply_markup=admin_users_keyboard())


@router.message(F.text == "⬅️ KANALLAR")
async def back_channels(message: Message, state: FSMContext, db: Database) -> None:
    if not await _guard(message, db):
        return
    await state.clear()
    await message.answer("📢 KANALLAR", reply_markup=admin_channels_keyboard())


@router.message(F.text == "⬅️ REYTING")
async def back_leaderboard(message: Message, state: FSMContext, db: Database) -> None:
    if not await _guard(message, db):
        return
    await state.clear()
    await message.answer("🏆 REYTING", reply_markup=admin_leaderboard_keyboard())


@router.message(F.text == "⬅️ TEST BOSHQARUVI")
async def back_quiz_management(message: Message, state: FSMContext, db: Database) -> None:
    if not await _guard(message, db):
        return
    await state.clear()
    await message.answer("🧠 TEST BOSHQARUVI", reply_markup=admin_quiz_keyboard())


@router.message(F.text == "⬅️ SOZLAMALAR")
async def back_settings(message: Message, state: FSMContext, db: Database) -> None:
    if not await _guard(message, db):
        return
    await state.clear()
    await message.answer("⚙️ SOZLAMALAR", reply_markup=admin_settings_keyboard())


@router.callback_query(F.data == "adm:content")
async def callback_content(callback: CallbackQuery, db: Database) -> None:
    if not await _guard(callback, db):
        await callback.answer()
        return
    await callback.answer()
    await callback.message.answer("📚 KONTENT", reply_markup=admin_content_keyboard())


@router.callback_query(F.data == "adm:channels")
async def callback_channels(callback: CallbackQuery, db: Database) -> None:
    if not await _guard(callback, db):
        await callback.answer()
        return
    await callback.answer()
    await callback.message.answer("📢 KANALLAR", reply_markup=admin_channels_keyboard())
