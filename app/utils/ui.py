from __future__ import annotations

from aiogram import Bot
from aiogram.types import Message

from app.keyboards.inline import subscription_keyboard
from app.keyboards.reply import main_keyboard
from app.services.admins import is_admin
from app.services.subscriptions import active_channels, is_subscribed_to_all
from app.database.session import Database


def progress_bar(current: int, total: int, width: int = 10) -> str:
    if total <= 0:
        return "░" * width
    filled = max(0, min(width, round(width * current / total)))
    return "█" * filled + "░" * (width - filled)


def panel(title: str, *lines: str) -> str:
    body = "\n".join(lines)
    if body:
        return f"╭─ {title} ─╮\n{body}\n╰{'─' * max(8, len(title) + 4)}╯"
    return f"╭─ {title} ─╮\n╰{'─' * max(8, len(title) + 4)}╯"


def menu_text() -> str:
    return (
        "📚 KITOBXONLAR\n\n"
        "Kitobni toping • kanalimizdagi ma’lumotni oching • bilimni test qiling.\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "📖 Mutolaa → 🧠 Test → 🏆 Natija\n"
        "━━━━━━━━━━━━━━━━"
    )


async def send_main_menu(message: Message, db: Database, bot: Bot) -> None:
    async with db.session() as session:
        admin = await is_admin(session, message.from_user.id)
    await message.answer(menu_text(), reply_markup=main_keyboard(admin))


async def require_subscription(message: Message, bot: Bot, db: Database) -> bool:
    async with db.session() as session:
        ok = await is_subscribed_to_all(session, bot, message.from_user.id)
        if ok:
            return True
        channels = await active_channels(session)
    await message.answer(
        "📢 BOTGA KIRISH\n\nAvval majburiy kanallarga obuna bo‘ling, so‘ng tekshiring.",
        reply_markup=subscription_keyboard(channels),
    )
    return False


async def require_callback_subscription(callback, bot: Bot, db: Database) -> bool:
    async with db.session() as session:
        ok = await is_subscribed_to_all(session, bot, callback.from_user.id)
        if ok:
            return True
        channels = await active_channels(session)
    await callback.message.answer(
        "⚠️ Avval barcha majburiy kanallarga obuna bo‘ling.",
        reply_markup=subscription_keyboard(channels),
    )
    return False
