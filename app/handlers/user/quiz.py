from __future__ import annotations

import random

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.config import get_settings
from app.database.models import Question, QuizAnswer, QuizAttempt
from app.database.session import Database
from app.keyboards.inline import book_list_keyboard
from app.keyboards.reply import answers_keyboard, quiz_count_keyboard, quiz_keyboard
from app.services.books import get_book, list_books
from app.services.quizzes import create_attempt, finish_attempt, get_questions, record_answer
from app.states.user import UserStates
from app.utils.ui import progress_bar, require_callback_subscription, require_subscription

router = Router(name="user_quiz")
settings = get_settings()


async def start_questions(message: Message, state: FSMContext, db: Database, question_ids: list[int], book_id: int | None) -> None:
    if not question_ids:
        await message.answer("📭 Hozircha bu rejim uchun savollar topilmadi.")
        return
    async with db.session() as session:
        from app.services.users import get_user
        user = await get_user(session, message.from_user.id)
        if not user:
            await message.answer("⚠️ Profil topilmadi. /start ni bosing.")
            return
        attempt = await create_attempt(session, user.id, book_id, len(question_ids))
    await state.set_state(UserStates.answering_quiz)
    await state.update_data(question_ids=question_ids, index=0, attempt_id=attempt.id, book_id=book_id, correct=0)
    await send_current_question(message, state, db)


async def send_current_question(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    ids = data.get("question_ids", [])
    index = int(data.get("index", 0))
    if index >= len(ids):
        await finish_quiz(message, state, db)
        return
    qid = int(ids[index])
    async with db.session() as session:
        question = await session.get(Question, qid)
    if not question:
        await state.update_data(index=index + 1)
        await send_current_question(message, state, db)
        return
    text = (
        f"📚 TEST\n\n"
        f"{progress_bar(index, len(ids))}  {index + 1}/{len(ids)}\n\n"
        f"❓ {question.text}\n\n"
        f"A) {question.option_a}\n"
        f"B) {question.option_b}\n"
        f"C) {question.option_c}\n"
        f"D) {question.option_d}"
    )
    await message.answer(text, reply_markup=answers_keyboard())


@router.message(F.text == "🧠 TEST")
async def quiz_home(message: Message, state: FSMContext, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    await state.clear()
    await message.answer("🧠 TEST\n\nBilimingizni sinash uchun rejimni tanlang.", reply_markup=quiz_keyboard())


@router.message(F.text == "📖 KITOB BO‘YICHA")
async def quiz_by_book(message: Message, state: FSMContext, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    async with db.session() as session:
        books = await list_books(session)
    if not books:
        await message.answer("📭 Hozircha kitoblar yo‘q.")
        return
    await state.set_state(UserStates.select_quiz_book)
    await message.answer("📖 Kitobni tanlang.", reply_markup=book_list_keyboard(books, back_callback="quiz:home"))


@router.callback_query(lambda c: c.data == "quiz:home")
async def quiz_home_callback(callback: CallbackQuery, state: FSMContext, db: Database, bot) -> None:
    if not await require_callback_subscription(callback, bot, db):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    await callback.message.answer("🧠 TEST\n\nBilimingizni sinash uchun rejimni tanlang.", reply_markup=quiz_keyboard())


@router.callback_query(lambda c: c.data and c.data.startswith("quizbook:"))
async def quiz_book_callback(callback: CallbackQuery, state: FSMContext, db: Database, bot) -> None:
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
    if not book:
        await callback.answer("Kitob topilmadi.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(UserStates.select_quiz_count)
    await state.update_data(book_id=book.id)
    await callback.message.answer(f"🧠 {book.title}\n\nNechta savol ishlaysiz?", reply_markup=quiz_count_keyboard())


@router.message(UserStates.select_quiz_count)
async def select_quiz_count(message: Message, state: FSMContext, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    mapping = {"5 TA": 5, "10 TA": 10, "20 TA": 20, "30 TA": 30}
    if message.text not in mapping:
        await message.answer("Savollar sonini tugmadan tanlang.")
        return
    data = await state.get_data()
    book_id = int(data["book_id"])
    async with db.session() as session:
        questions = await get_questions(session, book_id, mapping[message.text])
    await state.clear()
    await start_questions(message, state, db, [q.id for q in questions], book_id)


@router.message(F.text == "🎲 TASODIFIY TEST")
async def random_quiz(message: Message, state: FSMContext, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    async with db.session() as session:
        result = await session.execute(select(Question).where(Question.is_active.is_(True)))
        questions = list(result.scalars().all())
    random.shuffle(questions)
    questions = questions[: settings.default_quiz_questions]
    await state.clear()
    await start_questions(message, state, db, [q.id for q in questions], None)


@router.message(F.text == "🔥 BUGUNGI SAVOL")
async def daily_question(message: Message, state: FSMContext, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    from app.services.settings import get_setting
    async with db.session() as session:
        raw_id = await get_setting(session, "daily_question_id", "")
    if not raw_id.isdigit():
        await message.answer("📅 Bugungi savol hali belgilanmagan.")
        return
    await state.clear()
    await start_questions(message, state, db, [int(raw_id)], None)


@router.message(UserStates.answering_quiz, F.text == "⏹ TESTNI TO‘XTATISH")
async def stop_quiz(message: Message, state: FSMContext, db: Database, bot) -> None:
    await state.clear()
    if not await require_subscription(message, bot, db):
        return
    await message.answer("⏹ Test to‘xtatildi.", reply_markup=quiz_keyboard())


@router.message(UserStates.answering_quiz, F.text.in_({"🅰️ A", "🅱️ B", "©️ C", "🆎 D"}))
async def answer_question(message: Message, state: FSMContext, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    data = await state.get_data()
    ids = data.get("question_ids", [])
    index = int(data.get("index", 0))
    attempt_id = int(data["attempt_id"])
    if index >= len(ids):
        await finish_quiz(message, state, db)
        return
    async with db.session() as session:
        attempt = await session.get(QuizAttempt, attempt_id)
        question = await session.get(Question, int(ids[index]))
        if not attempt or not question:
            await state.update_data(index=index + 1)
            await send_current_question(message, state, db)
            return
        from app.services.settings import get_setting
        points = int(await get_setting(session, "points_per_correct", str(settings.points_per_correct)))
        selected = {"🅰️ A": "A", "🅱️ B": "B", "©️ C": "C", "🆎 D": "D"}[message.text]
        ok = await record_answer(session, attempt, question, selected, points)
        next_index = index + 1
        correct = int(data.get("correct", 0)) + int(ok)
    await state.update_data(index=next_index, correct=correct)
    await message.answer("✅ TO‘G‘RI! +{} ⭐".format(points) if ok else "❌ XATO!")
    await send_current_question(message, state, db)


async def finish_quiz(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    attempt_id = int(data.get("attempt_id", 0))
    if not attempt_id:
        await state.clear()
        return
    async with db.session() as session:
        attempt = await session.get(QuizAttempt, attempt_id)
        if not attempt:
            await state.clear()
            return
        await finish_attempt(session, attempt)
        total = attempt.total
        correct = attempt.correct
        score = attempt.score
    accuracy = round(correct / total * 100) if total else 0
    await state.clear()
    await message.answer(
        "🏆 TEST YAKUNLANDI\n\n"
        f"✅ To‘g‘ri: {correct}\n"
        f"❌ Xato: {total - correct}\n"
        f"🎯 Natija: {accuracy}%\n"
        f"⭐ Ball: {score}\n\n"
        "👏 Yaxshi ishladingiz!",
        reply_markup=quiz_keyboard(),
    )


@router.message(F.text == "❌ XATO SAVOLLARIM")
@router.message(F.text == "❌ XATOLARIM")
async def wrong_questions(message: Message, state: FSMContext, db: Database, bot) -> None:
    if not await require_subscription(message, bot, db):
        return
    from sqlalchemy import distinct
    async with db.session() as session:
        from app.database.models import User
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        if not user:
            await message.answer("Profil topilmadi.")
            return
        rows = await session.execute(
            select(distinct(QuizAnswer.question_id)).join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id).where(
                QuizAttempt.user_id == user.id, QuizAnswer.is_correct.is_(False)
            ).limit(30)
        )
        qids = [int(row[0]) for row in rows.all()]
    if not qids:
        await message.answer("✅ Hozircha xato javoblaringiz yo‘q.")
        return
    await state.clear()
    await start_questions(message, state, db, qids, None)
