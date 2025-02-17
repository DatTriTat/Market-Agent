from fastapi import HTTPException, Request

from app.core.config import Settings, get_settings
from app.core.mongo import MongoStore
from app.services.agent import ConversationAgent
from app.services.eodhd_client import EODHDClient
from app.services.session_cache import SessionCache
from app.services.stocks_service import StocksService


def get_session_cache(request: Request) -> SessionCache:
    return request.app.state.session_cache


def get_mongo_store(request: Request) -> MongoStore:
    store = getattr(request.app.state, "mongo_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="MongoDB is not configured.")
    return store


def get_eodhd_client(request: Request) -> EODHDClient:
    client = getattr(request.app.state, "eodhd_client", None)
    if client is None:
        raise HTTPException(status_code=503, detail="EODHD is not configured (missing API token).")
    return client


def get_stocks_service(request: Request) -> StocksService:
    svc = getattr(request.app.state, "stocks_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Stocks service is not configured.")
    return svc


def get_optional_stocks_service(request: Request) -> StocksService | None:
    return getattr(request.app.state, "stocks_service", None)


def get_agent(request: Request) -> ConversationAgent:
    return request.app.state.agent


def get_app_settings(request: Request) -> Settings:
    # Prefer app.state if already built, otherwise fall back to default loader.
    return getattr(request.app.state, "settings", None) or get_settings()
