import hashlib
import json
import logging
import time
from pathlib import Path

from aiogram import Bot
from aiogram.utils.web_app import WebAppUser, safe_parse_webapp_init_data
from aiohttp import web

import hotel_form
import hotel_requests
from settings import settings
from texts import lang_of
from topic_registry import redis

WEBAPP_DIR = Path(__file__).parent / "webapp"
INIT_DATA_MAX_AGE = 24 * 3600
# "pending" lives briefly so a crashed submit does not block retries; the result is kept for a day.
IDEMPOTENCY_PENDING_TTL, IDEMPOTENCY_RESULT_TTL = 60, 24 * 3600
BOT = web.AppKey("bot", Bot)
# Asset URLs carry a content hash, so clients never mix a new page with cached old scripts.
ASSET_VERSION = hashlib.sha256(b"".join(p.read_bytes() for p in sorted((WEBAPP_DIR / "assets").iterdir()))).hexdigest()[:12]
INDEX_HTML = (WEBAPP_DIR / "index.html").read_text().replace("__ASSET_VERSION__", ASSET_VERSION)


def error(status: int, code: str, **extra) -> web.Response:
    return web.json_response({"error": code, **extra}, status=status)


def authorize(request: web.Request) -> WebAppUser:
    # The user comes only from signed initData, never from the request body or URL.
    scheme, _, init_data = request.headers.get("Authorization", "").partition(" ")
    if scheme != "tma" or not init_data:
        raise web.HTTPUnauthorized()
    try:
        data = safe_parse_webapp_init_data(settings.bot_token, init_data)
    except ValueError:
        raise web.HTTPUnauthorized()
    if data.user is None or time.time() - data.auth_date.timestamp() > INIT_DATA_MAX_AGE:
        raise web.HTTPUnauthorized()
    allowed = settings.allowed_user_ids_set
    if allowed and data.user.id not in allowed:
        logging.warning(f"Blocked mini app request from unauthorized user {data.user.id}")
        raise web.HTTPForbidden()
    return data.user


def parse_request_id(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise web.HTTPBadRequest()


async def index(request: web.Request) -> web.Response:
    return web.Response(text=INDEX_HTML, content_type="text/html", headers={"Cache-Control": "no-cache"})


async def robots(request: web.Request) -> web.Response:
    return web.Response(text="User-agent: *\nDisallow: /\n")


async def add_noindex(request: web.Request, response: web.StreamResponse) -> None:
    # The form is reachable only from the bot; keep it out of search engines.
    response.headers["X-Robots-Tag"] = "noindex, nofollow"


async def get_request(request: web.Request) -> web.Response:
    user = authorize(request)
    try:
        status, topic_id, record = await hotel_requests.resolve(user.id, parse_request_id(request.query.get("request_id")))
    except LookupError:
        return error(404, "not_found")
    form = record.get("form") if record and status == hotel_requests.ACCEPTED else None
    preferences = await hotel_requests.get_preferences(user.id) if form is None else {}
    return web.json_response({"status": status, "request_id": topic_id, "form": form, "preferences": preferences,
                              "config": hotel_form.CONFIG})


async def submit_request(request: web.Request) -> web.Response:
    user = authorize(request)
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return error(400, "bad_json")
    key = str(body.get("idempotency_key") or "")
    if not 8 <= len(key) <= 64:
        return error(400, "bad_idempotency_key")
    request_id = parse_request_id(body.get("request_id"))
    try:
        form = hotel_form.clean_request(body.get("form") or {}, lang=lang_of(user.language_code))
    except hotel_form.ValidationError as e:
        return error(422, "validation", fields=e.errors)
    idempotency_key = f"request:idem:{user.id}:{key}"
    if not await redis.set(idempotency_key, "pending", nx=True, ex=IDEMPOTENCY_PENDING_TTL):
        cached = await redis.get(idempotency_key)
        if cached is None or cached == b"pending":
            return error(409, "in_progress")
        logging.info(f"Repeated mini app submit from user {user.id}, returning the saved result")
        return web.json_response(json.loads(cached))
    try:
        status, topic_id = await hotel_requests.submit(request.app[BOT], user, form, request_id)
    except LookupError:
        await redis.delete(idempotency_key)
        return error(404, "not_found")
    except Exception:
        await redis.delete(idempotency_key)
        logging.exception(f"Mini app submit failed for user {user.id}")
        return error(500, "internal")
    if status != hotel_requests.ACCEPTED:
        await redis.delete(idempotency_key)
        return error(409, status)
    result = {"status": status, "request_id": topic_id}
    await redis.set(idempotency_key, json.dumps(result), ex=IDEMPOTENCY_RESULT_TTL)
    return web.json_response(result)


def create_app(bot: Bot) -> web.Application:
    app = web.Application(client_max_size=64 * 1024)
    app[BOT] = bot
    app.on_response_prepare.append(add_noindex)
    app.router.add_get("/", index)
    app.router.add_get("/robots.txt", robots)
    app.router.add_static("/assets", WEBAPP_DIR / "assets")
    app.router.add_get("/api/request", get_request)
    app.router.add_post("/api/request", submit_request)
    return app


async def start(bot: Bot) -> web.AppRunner:
    runner = web.AppRunner(create_app(bot))
    await runner.setup()
    await web.TCPSite(runner, settings.webapp_host, settings.webapp_port).start()
    logging.info(f"Mini app served on {settings.webapp_host}:{settings.webapp_port}")
    return runner
