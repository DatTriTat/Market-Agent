from typing import cast

from langchain_core.tools import BaseTool, tool

from app.core.errors import UpstreamError
from app.services.eodhd_client import EODHDError
from app.services.stocks_service import StocksService


def _normalize_symbol(symbol: str, default_exchange: str) -> str:
    sym = (symbol or "").strip().upper()
    if not sym:
        return ""
    if "." not in sym:
        sym = sym + "." + default_exchange.upper()
    return sym


def build_stock_tools(stocks: StocksService, default_exchange: str = "US") -> list[BaseTool]:
    @tool("get_stock_context")
    def get_stock_context(symbol: str) -> str:
        """Get EOD stock data from MongoDB by symbol like AAPL.US."""
        sym = _normalize_symbol(symbol, default_exchange)
        if not sym:
            return "No symbol provided."
        return stocks.build_context(sym)

    @tool("get_universe_top")
    def get_universe_top(limit: int = 20) -> str:
        """Get top stocks by market cap from MongoDB."""
        if limit < 1:
            limit = 1
        if limit > 200:
            limit = 200
        return stocks.build_universe_top_context(limit=limit)

    @tool("get_stock_news")
    def get_stock_news(
        symbol: str,
        limit: int = 5,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> str:
        """Get recent news for a stock symbol like AAPL.US."""
        sym = _normalize_symbol(symbol, default_exchange)
        if not sym:
            return "No symbol provided."
        if limit < 1:
            limit = 1
        if limit > 20:
            limit = 20
        try:
            items = stocks.get_news_cached(
                symbol=sym,
                limit=limit,
                from_date=from_date,
                to_date=to_date,
                cache_hours=24,
                retention_days=30,
                default_exchange=default_exchange,
            )
        except (EODHDError, UpstreamError) as e:
            return f"[STOCK_NEWS] News unavailable for {sym}. Error: {e}"
        except Exception:
            return f"[STOCK_NEWS] News unavailable for {sym}."
        if not items:
            return f"[STOCK_NEWS] No news found for {sym}."

        lines: list[str] = []
        lines.append("[STOCK_NEWS]")
        lines.append(f"symbol: {sym}")
        rank = 0
        for item in items:
            rank += 1
            date = item.get("date") or item.get("datetime") or item.get("published") or ""
            title = item.get("title") or ""
            source = item.get("source") or item.get("source_name") or ""
            url = item.get("link") or item.get("url") or ""
            line = f"{rank}. {date} | {title}"
            if source:
                line = line + f" | source: {source}"
            if url:
                line = line + f" | url: {url}"
            lines.append(line.strip())
        return "\n".join(lines) + "\n"

    return cast(list[BaseTool], [get_stock_context, get_universe_top, get_stock_news])
