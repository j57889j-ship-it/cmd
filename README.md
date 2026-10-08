# Kitobxonlar Bot — V31

V31 is a clean, compact Telegram book-reader quiz bot built with aiogram 3.31, FastAPI, PostgreSQL and Redis/Valkey.

## Main user menu
- 📚 KITOBLAR
- 🧠 TEST
- 🏆 TOP
- 👤 PROFIL
- ℹ️ YORDAM
- Admin users additionally see 🛠 ADMIN

No referral system. No weekly/monthly/seasonal leaderboards. No HTML/Markdown parse mode is used for bot messages.

## Navigation fix
Back buttons are handled by dedicated navigation routers loaded before feature routers. This prevents generic state handlers from swallowing `⬅️ ASOSIY MENYU`, `⬅️ KITOBLAR`, `⬅️ TESTLAR` and admin back buttons.

## Book links
Each book can store:
- channel post URL
- detailed information URL
- cover photo

Users search the title/author and can open the admin-linked channel posts or start the quiz.

## Questions
- Manual question creation
- TXT import up to 100 questions
- Duplicate validation
- Book-specific quizzes
- Random quiz
- Daily question
- Wrong-answer retry
- Quiz progress bar
- Stop quiz button

## Channel reactions
Admins can enable automatic reactions for new posts in `TARGET_CHANNEL_ID` and choose a Telegram-supported emoji. The bot can set one bot reaction per message; `is_big=True` is used for the large animation when supported.

## Render
Build:
```bash
pip install -r requirements.txt
```

Start:
```bash
alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Environment
```text
BOT_TOKEN=
DATABASE_URL=
REDIS_URL=
ADMIN_IDS=
TARGET_CHANNEL_ID=
WEBHOOK_URL=
WEBHOOK_SECRET=
```
