from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SyncTopRequest(BaseModel):
    exchange: str = Field(default="us", description="Exchange filter for screener (e.g. us).")
    limit: int = Field(default=20, ge=1, le=200, description="How many symbols to sync.")
    min_market_cap: Optional[int] = Field(
        default=None, description="Optional market cap filter (USD)."
    )
    from_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    to_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    period: str = Field(default="d", description="d (daily), w (weekly), m (monthly)")


class SyncTopResponse(BaseModel):
    symbols: List[str]
    upserted_prices: int
    upserted_universe: int


class SyncSymbolsRequest(BaseModel):
    symbols: List[str] = Field(..., description="Symbols to sync, e.g. [AAPL.US, MSFT.US]")
    default_exchange: str = Field(default="US", description="Used if symbol has no exchange.")
    from_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    to_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    period: str = Field(default="d", description="d (daily), w (weekly), m (monthly)")


class SyncSymbolsResponse(BaseModel):
    symbols: List[str]
    upserted_prices: int


class BulkLastDayRequest(BaseModel):
    exchange_code: str = Field(default="US", description="Exchange code (e.g. US).")
    symbols: Optional[List[str]] = Field(
        default=None, description="Optional explicit symbol list (e.g. [AAPL.US])."
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=5000,
        description="Used only when symbols is null; picks top-N from stored universe.",
    )


class UniverseItem(BaseModel):
    symbol: str
    exchange: Optional[str] = None
    code: Optional[str] = None
    market_capitalization: Optional[float] = None
    raw: Optional[Dict[str, Any]] = None


class PriceDoc(BaseModel):
    symbol: str
    date: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    adjusted_close: Optional[float] = None
    volume: Optional[int] = None
    source: Optional[str] = None
    updated_at: Optional[str] = None


class PriceHistoryResponse(BaseModel):
    symbol: str
    items: List[PriceDoc]
