from aiogram import F, Router
from aiogram.types import Message, ReactionTypeEmoji

from app.config import get_settings
from app.services.settings import get_setting
from app.constants import SUPPORTED_REACTION_EMOJIS
from app.database.session import Database

router = Router(name="channel_reactions")
settings = get_settings()


@router.channel_post(F.chat.id == settings.target_channel_id)
async def auto_react_to_channel_post(message: Message, db: Database, bot) -> None:
    if not settings.target_channel_id:
        return
    async with db.session() as session:
        enabled = await get_setting(session, "reaction_enabled", "0")
        emoji = await get_setting(session, "reaction_emoji", "🔥")
    if enabled != "1" or emoji not in SUPPORTED_REACTION_EMOJIS:
        return
    try:
        await bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji=emoji)],
            is_big=True,
        )
    except Exception:
        # A channel may disallow that reaction or bot may lack the necessary rights.
        return
