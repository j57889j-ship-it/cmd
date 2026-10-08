from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI, Header, HTTPException, Request
from redis.asyncio import Redis

from app.config import get_settings
from app.database.session import Database
from app.handlers.admin import build_router as build_admin_router
from app.handlers.user import build_router as build_user_router
from app.handlers.channel_reactions import router as channel_reactions_router
from app.middlewares.admin_only import AdminOnlyMiddleware
from app.middlewares.user_context import UserContextMiddleware
from app.services.admins import ensure_super_admins

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("kitobxon_bot")

settings = get_settings()
db = Database(settings.database_url)
redis = Redis.from_url(settings.redis_url, decode_responses=False)
storage = RedisStorage(redis=redis)
bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=None))
dp = Dispatcher(storage=storage)

user_router = build_user_router()
admin_router = build_admin_router()
user_router.message.outer_middleware(UserContextMiddleware(db, settings))
user_router.callback_query.outer_middleware(UserContextMiddleware(db, settings))
admin_router.message.outer_middleware(UserContextMiddleware(db, settings))
admin_router.callback_query.outer_middleware(UserContextMiddleware(db, settings))
admin_router.message.outer_middleware(AdminOnlyMiddleware(db))
admin_router.callback_query.outer_middleware(AdminOnlyMiddleware(db))
dp.include_router(channel_reactions_router)
dp.include_router(user_router)
dp.include_router(admin_router)


async def prepare() -> None:
    async with db.session() as session:
        await ensure_super_admins(session, settings)
    try:
        await bot.set_my_commands([
            BotCommand(command="start", description="Botni boshlash"),
            BotCommand(command="help", description="Yordam"),
            BotCommand(command="cancel", description="Joriy amalni bekor qilish"),
        ])
    except Exception as exc:
        logger.warning("Bot commands sozlanmadi: %s", exc)


async def polling_runner() -> None:
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


@asynccontextmanager
async def lifespan(app: FastAPI):
    await prepare()
    task = None
    if settings.webhook_url:
        base = settings.webhook_url.rstrip("/")
        path = "/telegram/webhook"
        try:
            await bot.set_webhook(
                url=f"{base}{path}",
                secret_token=settings.webhook_secret,
                drop_pending_updates=False,
            )
            logger.info("Webhook o‘rnatildi: %s", path)
        except Exception as exc:
            logger.exception("Webhook o‘rnatilmadi: %s", exc)
    else:
        task = asyncio.create_task(polling_runner())
        logger.info("WEBHOOK_URL yo‘q — polling ishga tushdi")
    try:
        yield
    finally:
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await storage.close()
        await redis.close()
        await bot.session.close()
        await db.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/")
async def root():
    return {"ok": True, "service": settings.app_name}


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if settings.webhook_secret and x_telegram_bot_api_secret_token != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    from aiogram.types import Update
    payload = await request.json()
    update = Update.model_validate(payload, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}
