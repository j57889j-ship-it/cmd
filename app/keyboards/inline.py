from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def subscription_keyboard(channels) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for channel in channels:
        builder.row(InlineKeyboardButton(text=f"📢 {channel.title}", url=channel.invite_url))
    builder.row(InlineKeyboardButton(text="✅ OBUNANI TEKSHIRISH", callback_data="sub:check"))
    return builder.as_markup()


def book_list_keyboard(books, *, back_callback: str = "books:list") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for book in books:
        builder.row(InlineKeyboardButton(text=f"📖 {book.title}", callback_data=f"book:{book.id}"))
    builder.row(InlineKeyboardButton(text="⬅️ ORQAGA", callback_data=back_callback))
    return builder.as_markup()


def book_detail_keyboard(book, admin: bool = False, back_callback: str = "books:list") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if book.channel_url:
        builder.row(InlineKeyboardButton(text="📖 KITOB POSTI", url=book.channel_url))
    if book.detail_url:
        builder.row(InlineKeyboardButton(text="📚 BATAFSIL MA’LUMOT", url=book.detail_url))
    builder.row(InlineKeyboardButton(text="🧠 TESTNI BOSHLASH", callback_data=f"quizbook:{book.id}"))
    if admin:
        builder.row(InlineKeyboardButton(text="📢 KANALGA YUBORISH", callback_data=f"publish:{book.id}"))
    builder.row(InlineKeyboardButton(text="⬅️ ORQAGA", callback_data=back_callback))
    return builder.as_markup()


def back_keyboard(callback_data: str = "books:list") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ ORQAGA", callback_data=callback_data)]])


def admin_books_list_keyboard(books, prefix: str = "admbook") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for book in books:
        builder.row(InlineKeyboardButton(text=f"📖 {book.title}", callback_data=f"{prefix}:{book.id}"))
    builder.row(InlineKeyboardButton(text="⬅️ KONTENT", callback_data="adm:content"))
    return builder.as_markup()


def question_list_keyboard(questions, prefix: str = "admquestion") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for question in questions:
        title = question.text.replace("\n", " ")[:45]
        builder.row(InlineKeyboardButton(text=f"❓ {title}", callback_data=f"{prefix}:{question.id}"))
    builder.row(InlineKeyboardButton(text="⬅️ KONTENT", callback_data="adm:content"))
    return builder.as_markup()


def channels_list_keyboard(channels, prefix: str = "admchannel") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for channel in channels:
        status = "🟢" if channel.is_active else "🔴"
        builder.row(InlineKeyboardButton(text=f"{status} {channel.title}", callback_data=f"{prefix}:{channel.id}"))
    builder.row(InlineKeyboardButton(text="⬅️ KANALLAR", callback_data="adm:channels"))
    return builder.as_markup()


def reaction_presets_keyboard() -> InlineKeyboardMarkup:
    rows = [
        ["🔥", "❤", "👏", "🎉"],
        ["🤩", "💯", "🏆", "😍"],
        ["📚", "⚡", "👀", "🤝"],
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=e, callback_data=f"reaction:preset:{e}") for e in row]
            for row in rows
        ]
    )
