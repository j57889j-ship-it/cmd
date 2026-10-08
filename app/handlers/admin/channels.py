from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, delete

from app.database.models import Book, MandatoryChannel
from app.database.session import Database
from app.keyboards.inline import channels_list_keyboard
from app.keyboards.reply import admin_channels_keyboard
from app.services.settings import get_setting, set_setting
from app.constants import SUPPORTED_REACTION_EMOJIS
from app.keyboards.inline import reaction_presets_keyboard
from app.states.admin import AdminChannelStates, AdminReactionStates
from app.utils.auth import require_admin, can_manage_content, can_manage_users, is_super

router = Router(name="admin_channels")


@router.message(F.text == "📢 KANALLAR")
async def channels_home(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not role:
        return
    await message.answer("📢 KANALLAR", reply_markup=admin_channels_keyboard())


@router.message(F.text == "📡 MAJBURIY KANALLAR")
async def mandatory_channels(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not role:
        return
    async with db.session() as session:
        result = await session.execute(select(MandatoryChannel).order_by(MandatoryChannel.id))
        channels = list(result.scalars().all())
    if not channels:
        await message.answer("📭 Majburiy kanallar hali qo‘shilmagan.")
        return
    await message.answer("📡 MAJBURIY KANALLAR", reply_markup=channels_list_keyboard(channels))


@router.message(F.text == "➕ KANAL QO‘SHISH")
async def add_channel_start(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not role:
        return
    await state.set_state(AdminChannelStates.title)
    await message.answer("1/3 📢 Kanal nomini yuboring.")


@router.message(AdminChannelStates.title)
async def add_channel_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminChannelStates.chat_id)
    await message.answer("2/3 🆔 Kanal Chat ID sini yuboring. Masalan: -1001234567890")


@router.message(AdminChannelStates.chat_id)
async def add_channel_id(message: Message, state: FSMContext) -> None:
    if not message.text.lstrip("-").isdigit():
        await message.answer("Chat ID raqam bo‘lishi kerak.")
        return
    await state.update_data(chat_id=int(message.text))
    await state.set_state(AdminChannelStates.invite_url)
    await message.answer("3/3 🔗 Kanalga kirish linkini yuboring.")


@router.message(AdminChannelStates.invite_url)
async def add_channel_finish(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    async with db.session() as session:
        session.add(MandatoryChannel(title=data["title"], chat_id=int(data["chat_id"]), invite_url=message.text.strip(), is_active=True))
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            await message.answer("❌ Kanal saqlanmadi. Bu Chat ID allaqachon mavjud bo‘lishi mumkin.")
            return
    await state.clear()
    await message.answer("✅ Majburiy kanal qo‘shildi.", reply_markup=admin_channels_keyboard())


@router.callback_query(lambda c: c.data and c.data.startswith("admchannel:"))
async def channel_detail(callback: CallbackQuery, db: Database) -> None:
    role = await require_admin(callback, db)
    if not role:
        await callback.answer()
        return
    cid = int(callback.data.split(":", 1)[1])
    async with db.session() as session:
        channel = await session.get(MandatoryChannel, cid)
    if not channel:
        await callback.answer("Kanal topilmadi.", show_alert=True)
        return
    await callback.answer()
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢/🔴 HOLAT", callback_data=f"channel_toggle:{cid}")],
        [InlineKeyboardButton(text="🗑 O‘CHIRISH", callback_data=f"channel_delete:{cid}")],
    ])
    await callback.message.answer(f"📢 {channel.title}\n\n🆔 {channel.chat_id}\n🔗 {channel.invite_url}\n{'🟢 Faol' if channel.is_active else '🔴 O‘chiq'}", reply_markup=keyboard)


@router.callback_query(lambda c: c.data and c.data.startswith("channel_toggle:"))
async def toggle_channel(callback: CallbackQuery, db: Database) -> None:
    role = await require_admin(callback, db)
    if not role:
        await callback.answer()
        return
    cid = int(callback.data.split(":", 1)[1])
    async with db.session() as session:
        channel = await session.get(MandatoryChannel, cid)
        if not channel:
            await callback.answer("Kanal topilmadi.", show_alert=True)
            return
        channel.is_active = not channel.is_active
        await session.commit()
        state = channel.is_active
    await callback.answer("Faol" if state else "O‘chirildi")


@router.callback_query(lambda c: c.data and c.data.startswith("channel_delete:"))
async def delete_channel(callback: CallbackQuery, db: Database) -> None:
    role = await require_admin(callback, db)
    if not role:
        await callback.answer()
        return
    cid = int(callback.data.split(":", 1)[1])
    async with db.session() as session:
        await session.execute(delete(MandatoryChannel).where(MandatoryChannel.id == cid))
        await session.commit()
    await callback.answer("Kanal o‘chirildi ✅")
    await callback.message.edit_text("✅ Majburiy kanal o‘chirildi.")


@router.message(F.text == "❤️ REACTION")
async def reaction_home(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not role:
        return
    async with db.session() as session:
        enabled = await get_setting(session, "reaction_enabled", "0")
        emoji = await get_setting(session, "reaction_emoji", "🔥")
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢/🔴 ON/OFF", callback_data="reaction:toggle")],
        [InlineKeyboardButton(text="✏️ EMOJI", callback_data="reaction:set")],
    ])
    await message.answer(f"❤️ REACTION\n\nHolat: {'🟢 ON' if enabled == '1' else '🔴 OFF'}\nReaction: {emoji}\n\nBot kanalga tushgan yangi postga avtomatik reaction qo‘yadi.", reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "reaction:toggle")
async def reaction_toggle(callback: CallbackQuery, db: Database) -> None:
    role = await require_admin(callback, db)
    if not role:
        await callback.answer()
        return
    async with db.session() as session:
        current = await get_setting(session, "reaction_enabled", "0")
        await set_setting(session, "reaction_enabled", "0" if current == "1" else "1")
    await callback.answer("Reaction holati yangilandi")


@router.callback_query(lambda c: c.data == "reaction:set")
async def reaction_set(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    role = await require_admin(callback, db)
    if not role:
        await callback.answer()
        return
    await state.set_state(AdminReactionStates.emoji)
    await callback.answer()
    await callback.message.answer("❤️ Reaction tanlang. Telegram botlari hozircha bitta emoji reaction qo‘ya oladi.", reply_markup=reaction_presets_keyboard())


@router.callback_query(lambda c: c.data and c.data.startswith("reaction:preset:"))
async def reaction_preset(callback: CallbackQuery, db: Database, state: FSMContext) -> None:
    role = await require_admin(callback, db)
    if not role:
        await callback.answer()
        return
    emoji = callback.data.split(":", 2)[2]
    if emoji not in SUPPORTED_REACTION_EMOJIS:
        await callback.answer("Bu reaction qo‘llab-quvvatlanmaydi.", show_alert=True)
        return
    await state.clear()
    async with db.session() as session:
        await set_setting(session, "reaction_emoji", emoji)
    await callback.answer(f"Reaction: {emoji}")
    await callback.message.edit_text(f"✅ Reaction saqlandi: {emoji}")


@router.message(AdminReactionStates.emoji)
async def reaction_value(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not role:
        return
    value = (message.text or "").strip()
    if value not in SUPPORTED_REACTION_EMOJIS:
        await message.answer("⚠️ Telegram qo‘llab-quvvatlaydigan reactionlardan birini yuboring yoki yuqoridagi tugmadan tanlang.")
        return
    await state.clear()
    async with db.session() as session:
        await set_setting(session, "reaction_emoji", value)
    await message.answer(f"✅ Reaction saqlandi: {value}")


@router.callback_query(lambda c: c.data and c.data.startswith("publish:"))
async def publish_book(callback: CallbackQuery, db: Database, bot) -> None:
    role = await require_admin(callback, db)
    if not can_manage_content(role):
        await callback.answer()
        return
    from app.config import get_settings
    settings = get_settings()
    if not settings.target_channel_id:
        await callback.answer("TARGET_CHANNEL_ID sozlanmagan.", show_alert=True)
        return
    book_id = int(callback.data.split(":", 1)[1])
    async with db.session() as session:
        book = await session.get(Book, book_id)
        if not book:
            await callback.answer("Kitob topilmadi.", show_alert=True)
            return
        text = f"📚 {book.title}\n\n✍️ {book.author}\n\n{book.description}"
        from app.keyboards.inline import book_detail_keyboard
        markup = book_detail_keyboard(book)
    if book.cover_file_id:
        sent = await bot.send_photo(settings.target_channel_id, book.cover_file_id, caption=text, reply_markup=markup)
    else:
        sent = await bot.send_message(settings.target_channel_id, text, reply_markup=markup)
    await callback.answer("Kanalga yuborildi ✅")
