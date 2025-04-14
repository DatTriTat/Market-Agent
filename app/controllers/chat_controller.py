from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings
from app.core.dependencies import (
    get_agent,
    get_app_settings,
    get_optional_stocks_service,
    get_session_cache,
)
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, HistoryResponse
from app.services.agent import ConversationAgent
from app.services.session_cache import SessionCache
from app.services.stocks_service import StocksService
from app.services.stock_tools import build_stock_tools

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat_endpoint(
    payload: ChatRequest,
    agent: ConversationAgent = Depends(get_agent),
    cache: SessionCache = Depends(get_session_cache),
    settings: Settings = Depends(get_app_settings),
    stocks: StocksService | None = Depends(get_optional_stocks_service),
):
    if not payload.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id is required")
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    if payload.reset:
        cache.reset(payload.session_id)

    history = cache.get_history(payload.session_id)
    max_history = settings.agent.max_history
    if len(history) > max_history:
        history = history[-max_history:]

    context_text = (payload.context or "").strip()
    final_context = context_text if context_text else None

    tools = None
    if stocks is not None:
        tools = build_stock_tools(stocks, default_exchange=settings.eodhd.default_exchange)

    reply = agent.generate(
        user_message=payload.message,
        history=history,
        context=final_context,
        tools=tools,
    )

    cache.append(payload.session_id, "user", payload.message)
    cache.append(payload.session_id, "assistant", reply)
    latest_history = cache.get_history(payload.session_id)

    history_items: list[ChatMessage] = []
    for item in latest_history:
        history_items.append(
            ChatMessage(
                role=str(item.get("role") or "user"),
                content=str(item.get("content") or ""),
            )
        )

    return ChatResponse(
        session_id=payload.session_id,
        reply=reply,
        history=history_items,
    )


@router.delete("/{session_id}", status_code=204)
def reset_session(session_id: str, cache: SessionCache = Depends(get_session_cache)):
    cache.reset(session_id)


@router.get("/{session_id}", response_model=HistoryResponse)
def get_session_history(
    session_id: str,
    cache: SessionCache = Depends(get_session_cache),
):
    history_items: list[ChatMessage] = []
    for item in cache.get_history(session_id):
        history_items.append(
            ChatMessage(
                role=str(item.get("role") or "user"),
                content=str(item.get("content") or ""),
            )
        )
    return HistoryResponse(session_id=session_id, history=history_items)
