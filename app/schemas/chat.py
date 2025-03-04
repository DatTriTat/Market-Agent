from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role, e.g., user or assistant.")
    content: str = Field(..., description="Message text.")


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Opaque session identifier.")
    message: str = Field(..., description="User's new message.")
    context: Optional[str] = Field(
        default=None, description="Optional extra context for this turn."
    )
    reset: bool = Field(default=False, description="Reset the cached session before replying.")


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    history: List[ChatMessage]


class HistoryResponse(BaseModel):
    session_id: str
    history: List[ChatMessage]
