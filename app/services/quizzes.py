from __future__ import annotations

import random
from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Question, QuizAnswer, QuizAttempt, User


async def get_questions(session: AsyncSession, book_id: int, count: int) -> list[Question]:
    result = await session.execute(
        select(Question).where(Question.book_id == book_id, Question.is_active.is_(True)).order_by(Question.id)
    )
    rows = list(result.scalars().all())
    random.shuffle(rows)
    return rows[:count]


async def create_attempt(session: AsyncSession, user_id: int, book_id: int | None, total: int) -> QuizAttempt:
    attempt = QuizAttempt(user_id=user_id, book_id=book_id, total=total)
    session.add(attempt)
    await session.commit()
    await session.refresh(attempt)
    return attempt


async def record_answer(
    session: AsyncSession,
    attempt: QuizAttempt,
    question: Question,
    selected: str,
    correct_points: int,
) -> bool:
    is_correct = selected.upper() == question.correct_option.upper()
    session.add(
        QuizAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_option=selected.upper(),
            is_correct=is_correct,
        )
    )
    user = await session.get(User, attempt.user_id)
    if user is not None:
        user.total_questions += 1
        if is_correct:
            user.correct_answers += 1
            user.score += correct_points
            attempt.correct += 1
            attempt.score += correct_points
        else:
            user.wrong_answers += 1
    await session.commit()
    return is_correct


async def finish_attempt(session: AsyncSession, attempt: QuizAttempt) -> None:
    attempt.finished_at = datetime.now(timezone.utc)
    user = await session.get(User, attempt.user_id)
    if user:
        today = datetime.now(timezone.utc).date().isoformat()
        if user.last_quiz_day == today:
            pass
        else:
            # Streak is intentionally simple: one completed quiz per day continues it.
            from datetime import timedelta
            yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
            if user.last_quiz_day == yesterday:
                user.streak += 1
            else:
                user.streak = 1
            user.last_quiz_day = today
    await session.commit()


async def top_users(session: AsyncSession, limit: int) -> list[User]:
    result = await session.execute(select(User).where(User.is_blocked.is_(False)).order_by(User.score.desc(), User.id).limit(limit))
    return list(result.scalars().all())


async def user_rank(session: AsyncSession, score: int) -> int:
    result = await session.execute(select(func.count(User.id)).where(User.score > score, User.is_blocked.is_(False)))
    return int(result.scalar_one()) + 1
