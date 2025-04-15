import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.chat_controller import router as chat_router
from app.controllers.stocks_controller import router as stocks_router
from app.core.app_logging import setup_logging
from app.core.error_handlers import app_error_handler, unhandled_error_handler
from app.core.errors import AppError
from app.core.mongo import MongoStore
from app.core.config import Settings, get_settings
from app.middleware.process_time import ProcessTimeMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.services.agent import ConversationAgent
from app.services.eodhd_client import EODHDClient
from app.services.session_cache import SessionCache
from app.services.stocks_service import StocksService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging()
    app = FastAPI(title=settings.app.name)

    if settings.cors.enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors.allow_origins,
            allow_credentials=settings.cors.allow_credentials,
            allow_methods=settings.cors.allow_methods,
            allow_headers=settings.cors.allow_headers,
        )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(ProcessTimeMiddleware)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    app.state.settings = settings
    app.state.session_cache = SessionCache(
        redis_url=os.getenv(settings.redis.url_env) or settings.redis.url,
        key_prefix=settings.redis.key_prefix,
        ttl_seconds=settings.session_cache.ttl_seconds,
        max_messages=settings.session_cache.max_messages,
    )
    if settings.redis.verify_connection:
        app.state.session_cache.ping()

    try:
        app.state.mongo_store = MongoStore.from_config(settings.mongo)
        if settings.mongo.verify_connection:
            app.state.mongo_store.client.admin.command("ping")
    except Exception:
        app.state.mongo_store = None

    eodhd_token = (os.getenv(settings.eodhd.api_token_env) or settings.eodhd.api_token or "").strip()
    app.state.eodhd_client = (
        EODHDClient(api_token=eodhd_token, base_url=settings.eodhd.base_url) if eodhd_token else None
    )
    app.state.stocks_service = (
        StocksService(mongo=app.state.mongo_store, eodhd=app.state.eodhd_client)
        if app.state.eodhd_client is not None and app.state.mongo_store is not None
        else None
    )
    app.state.agent = ConversationAgent(
        openai_cfg=settings.openai,
        agent_cfg=settings.agent,
    )

    @app.get("/health", tags=["health"])
    def healthcheck():
        return {"status": "ok"}

    app.include_router(chat_router, prefix="/api")
    app.include_router(stocks_router, prefix="/api")
    return app


app = create_app()
