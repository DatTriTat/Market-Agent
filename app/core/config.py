from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.core.utils import load_yaml


class OpenAIConfig(BaseModel):
    model: str = "gpt-4.1"
    api_key: str | None = None
    api_key_env: str = "OPENAI_API_KEY"
    temperature: float = 0.6
    top_p: float = 1.0


class AgentConfig(BaseModel):
    system_prompt: str | None = None
    max_history: int = Field(default=16, ge=1)


class SessionCacheConfig(BaseModel):
    ttl_seconds: int = Field(default=7200, ge=60)
    max_messages: int = Field(default=20, ge=2)


class RedisConfig(BaseModel):
    url: str = "redis://localhost:6379/0"
    url_env: str = "REDIS_URL"
    key_prefix: str = "conv-agent"
    verify_connection: bool = False


class MongoConfig(BaseModel):
    uri: str = "mongodb://localhost:27017"
    uri_env: str = "MONGODB_URI"
    database: str = "market"
    verify_connection: bool = False


class EODHDConfig(BaseModel):
    api_token: str | None = None
    api_token_env: str = "EODHD_API_TOKEN"
    base_url: str = "https://eodhd.com/api"
    default_exchange: str = "US"
    verify_connection: bool = False


class CORSConfig(BaseModel):
    enabled: bool = True
    allow_origins: list[str] = Field(default_factory=lambda: ["*"])
    allow_credentials: bool = True
    allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])


class AppConfig(BaseModel):
    name: str = "Conversation Agent"


class Settings(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    session_cache: SessionCacheConfig = Field(default_factory=SessionCacheConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    mongo: MongoConfig = Field(default_factory=MongoConfig)
    eodhd: EODHDConfig = Field(default_factory=EODHDConfig)
    cors: CORSConfig = Field(default_factory=CORSConfig)


def _load_raw_config(path: str | Path) -> dict[str, Any]:
    cfg_path = Path(path)
    if not cfg_path.exists():
        return {}
    data = load_yaml(str(cfg_path)) or {}
    return data


def build_settings(path: str | Path = "config.yaml") -> Settings:
    raw = _load_raw_config(path)
    return Settings(
        app=AppConfig(**(raw.get("app") or {})),
        openai=OpenAIConfig(**(raw.get("openai") or {})),
        agent=AgentConfig(**(raw.get("agent") or {})),
        session_cache=SessionCacheConfig(**(raw.get("session_cache") or {})),
        redis=RedisConfig(**(raw.get("redis") or {})),
        mongo=MongoConfig(**(raw.get("mongo") or {})),
        eodhd=EODHDConfig(**(raw.get("eodhd") or {})),
        cors=CORSConfig(**(raw.get("cors") or {})),
    )


@lru_cache(maxsize=1)
def get_settings(path: str | Path = "config.yaml") -> Settings:
    return build_settings(path)
