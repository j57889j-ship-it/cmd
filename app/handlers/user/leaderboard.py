from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from app.database.models import User
from app.database.session import Database
from app.keyboards.reply import main_keyboard
from app.services.admins import is_admin
from app.services.quizzes import top_users, user_rank
from app.services.settings import get_setting
from app.utils.ui import require_subscription

router = Router(name="user_leaderboard")


@router.message(F.text == "🏆 TOP")
async def leaderboard(message: Message, state: FSMContext, db: Database, bot, settings) -> None:
    if not await require_subscription(message, bot, db):
        return
    await state.clear()
    async with db.session() as session:
        limit = int(await get_setting(session, "top_limit", str(settings.top_limit)))
        enabled = await get_setting(session, "top_enabled", "1")
        users = await top_users(session, limit) if enabled == "1" else []
        me = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        rank = await user_rank(session, me.score) if me else 0
    lines = ["🏆 TOP KITOBXONLAR", ""]
    medals = ["🥇", "🥈", "🥉"]
    for index, user in enumerate(users, start=1):
        name = f"@{user.username}" if user.username else user.first_name or str(user.telegram_id)
        medal = medals[index - 1] if index <= 3 else f"{index}."
        lines.append(f"{medal} {name} — {user.score} ⭐")
    lines.extend(["", "━━━━━━━━━━━━", f"👤 Siz: #{rank}", f"⭐ {me.score if me else 0} ball"])
    await message.answer("\n".join(lines))
