import asyncio
from aiohttp import web, ClientTimeout
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import (
    USE_WEBHOOK,
    WEBHOOK_BASE_URL,
    WEBHOOK_SECRET,
    WEBHOOK_PATH_PREFIX,
    WEBHOOK_HOST,
)
from logging_config import get_logger

logger = get_logger(__name__)


def create_resilient_bot(token: str, *, parse_mode: str = "HTML") -> Bot:
    timeout = ClientTimeout(total=45, connect=10, sock_connect=10, sock_read=35)
    session = AiohttpSession(timeout=timeout)
    return Bot(token=token, default=DefaultBotProperties(parse_mode=parse_mode), session=session)


def spawn_guarded_task(coro, *, name: str):
    task = asyncio.create_task(coro, name=name)

    def _done(t: asyncio.Task):
        try:
            exc = t.exception()
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.exception("Background task inspection failed name=%s err=%s", name, e)
            return
        if exc is not None:
            logger.exception("Background task crashed name=%s err=%s", name, exc)

    task.add_done_callback(_done)
    return task


async def run_bot_dispatcher(
    *,
    dp: Dispatcher,
    bot: Bot,
    bot_name: str,
    webhook_port: int,
) -> None:
    allowed_updates = dp.resolve_used_update_types()
    if not USE_WEBHOOK:
        logger.info("%s starting in polling mode", bot_name)
        await dp.start_polling(bot, allowed_updates=allowed_updates)
        return

    if not WEBHOOK_BASE_URL:
        raise RuntimeError("USE_WEBHOOK=true but WEBHOOK_BASE_URL is empty")

    path = f"/{WEBHOOK_PATH_PREFIX.strip('/')}/{bot_name}"
    webhook_url = f"{WEBHOOK_BASE_URL.rstrip('/')}{path}"
    secret = WEBHOOK_SECRET or None

    await bot.delete_webhook(drop_pending_updates=False)
    await bot.set_webhook(
        webhook_url,
        secret_token=secret,
        allowed_updates=allowed_updates,
    )
    logger.info("%s webhook registered url=%s", bot_name, webhook_url)

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=secret).register(app, path=path)
    setup_application(app, dp, bot=bot)

    async def health(_: web.Request) -> web.Response:
        return web.json_response({"ok": True, "bot": bot_name, "mode": "webhook"})

    app.router.add_get("/healthz", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEBHOOK_HOST, webhook_port)
    await site.start()
    logger.info("%s webhook server listening on %s:%s", bot_name, WEBHOOK_HOST, webhook_port)
    await asyncio.Event().wait()
