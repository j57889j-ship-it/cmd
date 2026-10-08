from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app.database.models import Book
from app.database.session import Database
from app.keyboards.inline import book_detail_keyboard, book_list_keyboard, back_keyboard
from app.keyboards.reply import books_keyboard
from app.services.books import book_question_count, get_book, list_books, search_books
from app.states.user import UserStates
from app.utils.ui import require_callback_subscription, require_subscription

router = Router(name="user_books")


@router.message(F.text == "📚 KITOBLAR")
async def books_home(message: Message, state: FSMContext, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    await state.clear()
    await message.answer("📚 KITOBLAR\n\nKitobni nomi yoki muallifi bo‘yicha qidiring.", reply_markup=books_keyboard())


@router.message(F.text == "🔎 KITOB QIDIRISH")
async def ask_book_search(message: Message, state: FSMContext, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    await state.set_state(UserStates.search_book)
    await message.answer("🔎 Kitob nomini yoki muallifini yozing.\n\nMasalan: O‘tkan kunlar")


@router.message(UserStates.search_book)
async def search_book_handler(message: Message, state: FSMContext, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    if not message.text or message.text.startswith("⬅️"):
        await state.clear()
        return
    async with db.session() as session:
        books = await search_books(session, message.text)
    await state.clear()
    if not books:
        await message.answer("📭 Bu nom bo‘yicha kitob topilmadi.\n\nBoshqa nom bilan qayta urinib ko‘ring.")
        return
    await message.answer("📚 TOPILGAN KITOBLAR\n\nKerakli kitobni tanlang:", reply_markup=book_list_keyboard(books))


@router.message(F.text == "📖 BARCHA KITOBLAR")
async def all_books(message: Message, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    async with db.session() as session:
        books = await list_books(session)
    if not books:
        await message.answer("📭 Hozircha kitoblar qo‘shilmagan.")
        return
    await message.answer("📚 BARCHA KITOBLAR", reply_markup=book_list_keyboard(books))


@router.callback_query(lambda c: c.data and c.data.startswith("book:"))
async def show_book(callback: CallbackQuery, db: Database, bot) -> None:
    if not await require_callback_subscription(callback, bot, db):
        await callback.answer()
        return
    try:
        book_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Noto‘g‘ri kitob.", show_alert=True)
        return
    async with db.session() as session:
        book = await get_book(session, book_id)
        if not book or not book.is_active:
            await callback.answer("Kitob topilmadi.", show_alert=True)
            return
        count = await book_question_count(session, book.id)
    await callback.answer()
    text = (
        f"📖 {book.title}\n\n"
        f"✍️ {book.author}\n\n"
        f"{book.description or 'Bu kitob uchun tavsif kiritilmagan.'}\n\n"
        f"❓ Savollar: {count} ta"
    )
    if book.cover_file_id:
        await callback.message.answer_photo(book.cover_file_id, caption=text, reply_markup=book_detail_keyboard(book))
    else:
        await callback.message.answer(text, reply_markup=book_detail_keyboard(book))


@router.callback_query(lambda c: c.data == "books:home")
async def books_home_callback(callback: CallbackQuery, db: Database, bot) -> None:
    if not await require_callback_subscription(callback, bot, db):
        await callback.answer()
        return
    await callback.answer()
    await callback.message.answer("📚 KITOBLAR\n\nKitobni nomi yoki muallifi bo‘yicha qidiring.", reply_markup=books_keyboard())


@router.callback_query(lambda c: c.data == "books:list")
async def books_list_back(callback: CallbackQuery, db: Database, bot) -> None:
    if not await require_callback_subscription(callback, bot, db):
        await callback.answer()
        return
    async with db.session() as session:
        books = await list_books(session)
    await callback.answer()
    await callback.message.answer("📚 KITOBLAR", reply_markup=book_list_keyboard(books) if books else back_keyboard("books:home"))
