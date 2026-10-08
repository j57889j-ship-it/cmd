from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import delete, select

from app.constants import CANCEL
from app.database.models import Book, Question
from app.database.session import Database
from app.keyboards.inline import admin_books_list_keyboard, book_list_keyboard, book_detail_keyboard, question_list_keyboard
from app.keyboards.reply import admin_content_keyboard, admin_books_keyboard, admin_questions_keyboard
from app.services.books import normalize_text
from app.states.admin import AdminBookStates, AdminImportStates, AdminQuestionStates
from app.utils.auth import can_manage_content, require_admin
from app.utils.txt_import import parse_txt

router = Router(name="admin_content")


@router.message(F.text == "📚 KONTENT")
async def content_home(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_content(role):
        return
    await message.answer("📚 KONTENT\n\nKitoblar, savollar va TXT import shu bo‘limda.", reply_markup=admin_content_keyboard())


@router.message(F.text == "📖 KITOBLARNI BOSHQARISH")
async def books_manage(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_content(role):
        return
    await message.answer("📖 KITOBLARNI BOSHQARISH", reply_markup=admin_books_keyboard())


@router.message(F.text == "➕ KITOB QO‘SHISH")
async def add_book_start(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_content(role):
        return
    await state.set_state(AdminBookStates.title)
    await message.answer("1/6 📖 Kitob nomini yuboring.")


@router.message(AdminBookStates.title)
async def add_book_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminBookStates.author)
    await message.answer("2/6 ✍️ Muallifni yuboring.")


@router.message(AdminBookStates.author)
async def add_book_author(message: Message, state: FSMContext) -> None:
    await state.update_data(author=message.text.strip())
    await state.set_state(AdminBookStates.description)
    await message.answer("3/6 📝 Kitob haqida qisqa ma’lumot yuboring.")


@router.message(AdminBookStates.description)
async def add_book_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await state.set_state(AdminBookStates.channel_url)
    await message.answer("4/6 🔗 Asosiy kanal postining to‘liq linkini yuboring. Link bo‘lmasa - yozing.")


@router.message(AdminBookStates.channel_url)
async def add_book_channel_url(message: Message, state: FSMContext) -> None:
    await state.update_data(channel_url=None if message.text.strip() == "-" else message.text.strip())
    await state.set_state(AdminBookStates.detail_url)
    await message.answer("5/6 🔗 Batafsil ma’lumot postining to‘liq linkini yuboring. Link bo‘lmasa - yozing.")


@router.message(AdminBookStates.detail_url)
async def add_book_detail_url(message: Message, state: FSMContext) -> None:
    await state.update_data(detail_url=None if message.text.strip() == "-" else message.text.strip())
    await state.set_state(AdminBookStates.cover)
    await message.answer("6/6 🖼 Muqova rasmini yuboring. Muqova kerak bo‘lmasa O‘TKAZISH deb yozing.")


@router.message(AdminBookStates.cover)
async def add_book_cover(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_content(role):
        return
    data = await state.get_data()
    cover_file_id = message.photo[-1].file_id if message.photo else None
    if not message.photo and (not message.text or message.text.strip().upper() not in {"O‘TKAZISH", "SKIP", "-"}):
        await message.answer("🖼 Rasm yuboring yoki O‘TKAZISH deb yozing.")
        return
    async with db.session() as session:
        book = Book(
            title=data["title"],
            author=data["author"],
            description=data["description"],
            channel_url=data.get("channel_url"),
            detail_url=data.get("detail_url"),
            cover_file_id=cover_file_id,
            is_active=True,
        )
        session.add(book)
        await session.commit()
    await state.clear()
    await message.answer("✅ Kitob muvaffaqiyatli qo‘shildi.", reply_markup=admin_books_keyboard())


@router.message(F.text == "🔎 KITOB TOPISH")
async def find_book(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_content(role):
        return
    await state.set_state(AdminBookStates.find)
    await message.answer("🔎 Kitob nomini yuboring.")


@router.message(AdminBookStates.find)
async def find_book_value(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_content(role):
        return
    from app.services.books import search_books
    async with db.session() as session:
        books = await search_books(session, message.text)
    await state.clear()
    if not books:
        await message.answer("📭 Kitob topilmadi.")
        return
    await message.answer("📚 TOPILDI", reply_markup=admin_books_list_keyboard(books, "admbook"))


@router.callback_query(lambda c: c.data and c.data.startswith("admbook:"))
async def admin_book_details(callback: CallbackQuery, db: Database) -> None:
    role = await require_admin(callback, db)
    if not can_manage_content(role):
        await callback.answer()
        return
    book_id = int(callback.data.split(":", 1)[1])
    async with db.session() as session:
        book = await session.get(Book, book_id)
        if not book:
            await callback.answer("Kitob topilmadi.", show_alert=True)
            return
        qcount = await session.scalar(select(Question.id).where(Question.book_id == book.id).limit(1))
    await callback.answer()
    text = f"📖 {book.title}\n\n✍️ {book.author}\n\n{book.description}\n\n{'✅' if book.is_active else '🔴'} Holat"
    await callback.message.answer(text, reply_markup=book_detail_keyboard(book, admin=True, back_callback="adm:content"))


@router.message(F.text == "🗑 KITOB O‘CHIRISH")
async def delete_book_start(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_content(role):
        return
    await state.set_state(AdminBookStates.delete)
    await message.answer("🗑 O‘chiriladigan kitob nomini yuboring.")


@router.message(AdminBookStates.delete)
async def delete_book_value(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_content(role):
        return
    from app.services.books import search_books, delete_book
    async with db.session() as session:
        books = await search_books(session, message.text, limit=10)
        if not books:
            await message.answer("📭 Kitob topilmadi.")
            return
        if len(books) > 1:
            await state.clear()
            await message.answer("Bir nechta kitob topildi. Kerakli kitobni tanlang.", reply_markup=admin_books_list_keyboard(books, "deletebook"))
            return
        target = books[0]
        await delete_book(session, target.id)
    await state.clear()
    await message.answer(f"✅ {target.title} o‘chirildi.", reply_markup=admin_books_keyboard())


@router.callback_query(lambda c: c.data and c.data.startswith("deletebook:"))
async def delete_book_callback(callback: CallbackQuery, db: Database) -> None:
    role = await require_admin(callback, db)
    if not can_manage_content(role):
        await callback.answer()
        return
    book_id = int(callback.data.split(":", 1)[1])
    from app.services.books import delete_book, get_book
    async with db.session() as session:
        book = await get_book(session, book_id)
        if not book:
            await callback.answer("Kitob topilmadi.", show_alert=True)
            return
        title = book.title
        await delete_book(session, book_id)
    await callback.answer("O‘chirildi ✅")
    await callback.message.answer(f"✅ {title} o‘chirildi.", reply_markup=admin_books_keyboard())


@router.message(F.text == "❓ SAVOLLARNI BOSHQARISH")
async def questions_manage(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_content(role):
        return
    await message.answer("❓ SAVOLLARNI BOSHQARISH", reply_markup=admin_questions_keyboard())


@router.message(F.text == "➕ SAVOL QO‘SHISH")
async def add_question_start(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_content(role):
        return
    async with db.session() as session:
        result = await session.execute(select(Book).where(Book.is_active.is_(True)).order_by(Book.title).limit(30))
        books = list(result.scalars().all())
    if not books:
        await message.answer("Avval kamida bitta kitob qo‘shing.")
        return
    await state.set_state(AdminQuestionStates.book)
    await message.answer("📖 Kitob ID sini yuboring:\n\n" + "\n".join(f"{b.id} — {b.title}" for b in books))


@router.message(AdminQuestionStates.book)
async def add_question_book(message: Message, state: FSMContext, db: Database) -> None:
    if not message.text.isdigit():
        await message.answer("Kitob ID raqamini yuboring.")
        return
    async with db.session() as session:
        book = await session.get(Book, int(message.text))
    if not book:
        await message.answer("Bunday kitob yo‘q.")
        return
    await state.update_data(book_id=book.id)
    await state.set_state(AdminQuestionStates.text)
    await message.answer("Savol matnini yuboring.")


@router.message(AdminQuestionStates.text)
async def add_question_text(message: Message, state: FSMContext) -> None:
    await state.update_data(text=message.text.strip())
    await state.set_state(AdminQuestionStates.option_a)
    await message.answer("A variantni yuboring.")


@router.message(AdminQuestionStates.option_a)
async def add_question_a(message: Message, state: FSMContext) -> None:
    await state.update_data(option_a=message.text.strip())
    await state.set_state(AdminQuestionStates.option_b)
    await message.answer("B variantni yuboring.")


@router.message(AdminQuestionStates.option_b)
async def add_question_b(message: Message, state: FSMContext) -> None:
    await state.update_data(option_b=message.text.strip())
    await state.set_state(AdminQuestionStates.option_c)
    await message.answer("C variantni yuboring.")


@router.message(AdminQuestionStates.option_c)
async def add_question_c(message: Message, state: FSMContext) -> None:
    await state.update_data(option_c=message.text.strip())
    await state.set_state(AdminQuestionStates.option_d)
    await message.answer("D variantni yuboring.")


@router.message(AdminQuestionStates.option_d)
async def add_question_d(message: Message, state: FSMContext) -> None:
    await state.update_data(option_d=message.text.strip())
    await state.set_state(AdminQuestionStates.correct)
    await message.answer("To‘g‘ri javob harfini yuboring: A / B / C / D")


@router.message(AdminQuestionStates.correct)
async def add_question_correct(message: Message, state: FSMContext) -> None:
    value = message.text.strip().upper()
    if value not in {"A", "B", "C", "D"}:
        await message.answer("Faqat A, B, C yoki D.")
        return
    await state.update_data(correct=value)
    await state.set_state(AdminQuestionStates.explanation)
    await message.answer("Izoh bo‘lsa yuboring. Kerak bo‘lmasa - yozing.")


@router.message(AdminQuestionStates.explanation)
async def add_question_finish(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    async with db.session() as session:
        q = Question(
            book_id=int(data["book_id"]), text=data["text"], normalized_text=normalize_text(data["text"]),
            option_a=data["option_a"], option_b=data["option_b"], option_c=data["option_c"], option_d=data["option_d"],
            correct_option=data["correct"], explanation="" if message.text.strip() == "-" else message.text.strip(), is_active=True,
        )
        session.add(q)
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            await message.answer("❌ Savol saqlanmadi. Xuddi shu kitobda shu savol allaqachon bor bo‘lishi mumkin.")
            return
    await state.clear()
    await message.answer("✅ Savol qo‘shildi.", reply_markup=admin_questions_keyboard())


@router.message(F.text == "📋 SAVOLLAR RO‘YXATI")
async def question_list(message: Message, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_content(role):
        return
    async with db.session() as session:
        result = await session.execute(select(Question).where(Question.is_active.is_(True)).order_by(Question.id.desc()).limit(30))
        questions = list(result.scalars().all())
    await message.answer("📋 SAVOLLAR", reply_markup=question_list_keyboard(questions))


@router.message(F.text == "📥 TXT IMPORT")
async def txt_import_start(message: Message, state: FSMContext, db: Database) -> None:
    role = await require_admin(message, db)
    if not can_manage_content(role):
        return
    async with db.session() as session:
        result = await session.execute(select(Book).where(Book.is_active.is_(True)).order_by(Book.title).limit(50))
        books = list(result.scalars().all())
    await state.set_state(AdminImportStates.book)
    await message.answer("📥 TXT IMPORT\n\nAvval kitob ID sini yuboring:\n\n" + "\n".join(f"{b.id} — {b.title}" for b in books))


@router.message(AdminImportStates.book)
async def import_book(message: Message, state: FSMContext, db: Database) -> None:
    if not message.text.isdigit():
        await message.answer("Kitob ID raqamini yuboring.")
        return
    async with db.session() as session:
        book = await session.get(Book, int(message.text))
    if not book:
        await message.answer("Kitob topilmadi.")
        return
    await state.update_data(book_id=book.id)
    await state.set_state(AdminImportStates.file)
    await message.answer("📄 TXT faylni yuboring. Maksimum 100 ta savol.")


@router.message(AdminImportStates.file, F.document)
async def import_file(message: Message, state: FSMContext, db: Database, bot) -> None:
    role = await require_admin(message, db)
    if not can_manage_content(role):
        return
    if not message.document.file_name.lower().endswith(".txt"):
        await message.answer("Faqat .txt fayl yuboring.")
        return
    data = await state.get_data()
    file_info = await bot.get_file(message.document.file_id)
    buffer = await bot.download_file(file_info.file_path)
    content = buffer.read().decode("utf-8", errors="replace")
    parsed, errors, duplicates = parse_txt(content, 100)
    async with db.session() as session:
        existing_result = await session.execute(select(Question.normalized_text).where(Question.book_id == int(data["book_id"])))
        existing = set(existing_result.scalars().all())
        new_rows = []
        skipped_existing = 0
        for item in parsed:
            normalized = normalize_text(item.text)
            if normalized in existing:
                skipped_existing += 1
                continue
            existing.add(normalized)
            new_rows.append(Question(book_id=int(data["book_id"]), text=item.text, normalized_text=normalized, option_a=item.option_a, option_b=item.option_b, option_c=item.option_c, option_d=item.option_d, correct_option=item.correct_option, explanation=item.explanation, is_active=True))
        session.add_all(new_rows)
        await session.commit()
    await state.clear()
    summary = (
        "📥 IMPORT NATIJASI\n\n"
        f"✅ Yangi savollar: {len(new_rows)}\n"
        f"🔁 Fayl duplicate: {duplicates}\n"
        f"📦 Bazadagi duplicate: {skipped_existing}\n"
        f"⚠️ Xatolar: {len(errors)}"
    )
    if errors:
        summary += "\n\n" + "\n".join(errors[:10])
    await message.answer(summary, reply_markup=admin_content_keyboard())

@router.callback_query(lambda c: c.data and c.data.startswith("admquestion:"))
async def admin_question_details(callback: CallbackQuery, db: Database) -> None:
    role = await require_admin(callback, db)
    if not can_manage_content(role):
        await callback.answer()
        return
    qid = int(callback.data.split(":", 1)[1])
    async with db.session() as session:
        q = await session.get(Question, qid)
        if not q:
            await callback.answer("Savol topilmadi.", show_alert=True)
            return
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗑 O‘CHIRISH", callback_data=f"deletequestion:{qid}")]])
    await callback.answer()
    await callback.message.answer(
        f"❓ {q.text}\n\nA) {q.option_a}\nB) {q.option_b}\nC) {q.option_c}\nD) {q.option_d}\n\n✅ Javob: {q.correct_option}",
        reply_markup=kb,
    )


@router.callback_query(lambda c: c.data and c.data.startswith("deletequestion:"))
async def delete_question(callback: CallbackQuery, db: Database) -> None:
    role = await require_admin(callback, db)
    if not can_manage_content(role):
        await callback.answer()
        return
    qid = int(callback.data.split(":", 1)[1])
    async with db.session() as session:
        q = await session.get(Question, qid)
        if not q:
            await callback.answer("Savol topilmadi.", show_alert=True)
            return
        await session.delete(q)
        await session.commit()
    await callback.answer("Savol o‘chirildi ✅")
    await callback.message.edit_text("✅ Savol o‘chirildi.")
