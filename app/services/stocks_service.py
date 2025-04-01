from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Iterable

from pymongo import UpdateOne

from app.core.errors import UpstreamError
from app.core.mongo import MongoStore
from app.services.eodhd_client import EODHDClient, EODHDError


def _to_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _to_int(v: Any) -> int | None:
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


def _iso_today() -> str:
    return dt.date.today().isoformat()


@dataclass(frozen=True)
class SyncResult:
    symbols: list[str]
    upserted_prices: int
    upserted_universe: int


@dataclass(frozen=True)
class SyncSymbolsResult:
    symbols: list[str]
    upserted_prices: int


@dataclass(frozen=True)
class StocksService:
    mongo: MongoStore
    eodhd: EODHDClient

    @property
    def prices(self):
        return self.mongo.db["prices_daily"]

    @property
    def universe(self):
        return self.mongo.db["universe"]

    @property
    def news(self):
        return self.mongo.db["news"]

    def _symbol_from_item(self, item: dict[str, Any], default_exchange: str = "US") -> str:
        code = str(item.get("code") or item.get("Code") or "").strip()
        exch = str(item.get("exchange") or item.get("Exchange") or default_exchange).strip()
        if not code:
            raise ValueError("Missing code in screener item")
        return f"{code}.{exch.upper()}"

    def _normalize_symbol(self, symbol: str, default_exchange: str = "US") -> str:
        sym = str(symbol or "").strip().upper()
        if not sym:
            return ""
        if "." not in sym:
            sym = sym + "." + default_exchange.upper()
        return sym

    def get_news_cached(
        self,
        symbol: str,
        limit: int = 5,
        from_date: str | None = None,
        to_date: str | None = None,
        cache_hours: int = 24,
        retention_days: int = 30,
        default_exchange: str = "US",
    ) -> list[dict[str, Any]]:
        sym = self._normalize_symbol(symbol, default_exchange=default_exchange)
        if not sym:
            return []

        if limit < 1:
            limit = 1
        if limit > 50:
            limit = 50

        now = dt.datetime.utcnow()
        fresh_cutoff = now - dt.timedelta(hours=cache_hours)
        retention_cutoff = now - dt.timedelta(days=retention_days)

        can_use_cache = from_date is None and to_date is None
        if can_use_cache:
            cur = (
                self.news.find(
                    {"symbol": sym, "fetched_at": {"$gte": fresh_cutoff}},
                    projection={"_id": 0},
                )
                .sort("date", -1)
                .limit(int(limit))
            )
            cached = list(cur)
            if cached:
                return cached

        try:
            if not from_date:
                from_date = retention_cutoff.date().isoformat()
            items = self.eodhd.news(
                symbol=sym,
                from_date=from_date,
                to_date=to_date,
                limit=limit,
                offset=0,
            )
        except EODHDError as e:
            raise UpstreamError(f"EODHD news failed: {e}")

        if not items:
            return []

        ops: list[UpdateOne] = []
        for item in items:
            title = str(item.get("title") or "").strip()
            url = str(item.get("link") or item.get("url") or "").strip()
            date = str(item.get("date") or item.get("datetime") or item.get("published") or "").strip()
            source = str(item.get("source") or item.get("source_name") or "").strip()
            doc = {
                "symbol": sym,
                "title": title,
                "url": url or None,
                "date": date,
                "source": source or None,
                "raw": item,
                "fetched_at": now,
            }
            key: dict[str, Any] = {"symbol": sym}
            if url:
                key["url"] = url
            elif title and date:
                key["title"] = title
                key["date"] = date
            else:
                key["title"] = title
            ops.append(UpdateOne(key, {"$set": doc}, upsert=True))

        if ops:
            self.news.bulk_write(ops, ordered=False)

        return items

    def get_top_symbols(
        self,
        exchange: str = "us",
        limit: int = 20,
        min_market_cap: int | None = None,
    ) -> list[dict[str, Any]]:
        filters: list[list[Any]] = [["exchange", "=", exchange.lower()]]
        if min_market_cap is not None:
            filters.append(["market_capitalization", ">", int(min_market_cap)])
        return self.eodhd.screener(
            filters=filters,
            sort="market_capitalization.desc",
            limit=limit,
            offset=0,
        )

    def sync_top_eod(
        self,
        exchange: str = "us",
        limit: int = 20,
        min_market_cap: int | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        period: str = "d",
    ) -> SyncResult:
        try:
            items = self.get_top_symbols(exchange=exchange, limit=limit, min_market_cap=min_market_cap)

            symbols: list[str] = []
            upserted_universe = 0
            for item in items:
                try:
                    symbol = self._symbol_from_item(item, default_exchange=exchange.upper())
                except Exception:
                    continue
                symbols.append(symbol)
                doc = dict(item)
                doc["symbol"] = symbol
                doc["exchange"] = str(item.get("exchange") or item.get("Exchange") or exchange).lower()
                res = self.universe.update_one(
                    {"exchange": doc["exchange"], "code": doc.get("code") or doc.get("Code")},
                    {"$set": doc},
                    upsert=True,
                )
                if getattr(res, "upserted_id", None) is not None:
                    upserted_universe += 1

            upserted_prices = 0
            for symbol in symbols:
                records = self.eodhd.eod(
                    symbol=symbol,
                    from_date=from_date,
                    to_date=to_date,
                    period=period,
                    order="a",
                )
                if not records:
                    continue

                ops: list[UpdateOne] = []
                for r in records:
                    date = str(r.get("date") or "").strip()
                    if not date:
                        continue
                    doc = {
                        "symbol": symbol,
                        "date": date,
                        "open": _to_float(r.get("open")),
                        "high": _to_float(r.get("high")),
                        "low": _to_float(r.get("low")),
                        "close": _to_float(r.get("close")),
                        "adjusted_close": _to_float(r.get("adjusted_close") or r.get("adjustedClose")),
                        "volume": _to_int(r.get("volume")),
                        "source": "eodhd",
                        "updated_at": dt.datetime.utcnow().isoformat(),
                    }
                    ops.append(UpdateOne({"symbol": symbol, "date": date}, {"$set": doc}, upsert=True))

                if ops:
                    res = self.prices.bulk_write(ops, ordered=False)
                    upserted_prices += int(getattr(res, "upserted_count", 0) or 0)
                    upserted_prices += int(getattr(res, "modified_count", 0) or 0)

            return SyncResult(
                symbols=symbols,
                upserted_prices=upserted_prices,
                upserted_universe=upserted_universe,
            )
        except EODHDError as e:
            raise UpstreamError(f"EODHD sync failed: {e}")

    def sync_bulk_last_day(self, exchange_code: str = "US", symbols: Iterable[str] | None = None) -> int:
        try:
            wanted: set[str] = set()
            if symbols:
                for sym in symbols:
                    if sym:
                        wanted.add(sym.upper())
            records = self.eodhd.eod_bulk_last_day(exchange_code=exchange_code)
            if not records:
                return 0

            ops: list[UpdateOne] = []
            for r in records:
                code = str(r.get("code") or r.get("Code") or r.get("symbol") or "").strip()
                date = str(r.get("date") or "").strip()
                if not code or not date:
                    continue
                symbol = code if "." in code else f"{code}.{exchange_code.upper()}"
                if wanted and symbol.upper() not in wanted:
                    continue
                doc = {
                    "symbol": symbol,
                    "date": date,
                    "open": _to_float(r.get("open")),
                    "high": _to_float(r.get("high")),
                    "low": _to_float(r.get("low")),
                    "close": _to_float(r.get("close")),
                    "adjusted_close": _to_float(r.get("adjusted_close") or r.get("adjustedClose")),
                    "volume": _to_int(r.get("volume")),
                    "source": "eodhd",
                    "updated_at": dt.datetime.utcnow().isoformat(),
                }
                ops.append(UpdateOne({"symbol": symbol, "date": date}, {"$set": doc}, upsert=True))

            if not ops:
                return 0
            res = self.prices.bulk_write(ops, ordered=False)
            return int(getattr(res, "upserted_count", 0) or 0) + int(
                getattr(res, "modified_count", 0) or 0
            )
        except EODHDError as e:
            raise UpstreamError(f"EODHD bulk sync failed: {e}")

    def sync_symbols(
        self,
        symbols: Iterable[str],
        default_exchange: str = "US",
        from_date: str | None = None,
        to_date: str | None = None,
        period: str = "d",
    ) -> SyncSymbolsResult:
        try:
            final_symbols: list[str] = []
            seen: set[str] = set()
            for symbol in symbols or []:
                norm = self._normalize_symbol(symbol, default_exchange=default_exchange)
                if not norm:
                    continue
                if norm in seen:
                    continue
                seen.add(norm)
                final_symbols.append(norm)

            upserted_prices = 0
            for symbol in final_symbols:
                records = self.eodhd.eod(
                    symbol=symbol,
                    from_date=from_date,
                    to_date=to_date,
                    period=period,
                    order="a",
                )
                if not records:
                    continue

                ops: list[UpdateOne] = []
                for r in records:
                    date = str(r.get("date") or "").strip()
                    if not date:
                        continue
                    doc = {
                        "symbol": symbol,
                        "date": date,
                        "open": _to_float(r.get("open")),
                        "high": _to_float(r.get("high")),
                        "low": _to_float(r.get("low")),
                        "close": _to_float(r.get("close")),
                        "adjusted_close": _to_float(r.get("adjusted_close") or r.get("adjustedClose")),
                        "volume": _to_int(r.get("volume")),
                        "source": "eodhd",
                        "updated_at": dt.datetime.utcnow().isoformat(),
                    }
                    ops.append(UpdateOne({"symbol": symbol, "date": date}, {"$set": doc}, upsert=True))

                if ops:
                    res = self.prices.bulk_write(ops, ordered=False)
                    upserted_prices += int(getattr(res, "upserted_count", 0) or 0)
                    upserted_prices += int(getattr(res, "modified_count", 0) or 0)

            return SyncSymbolsResult(symbols=final_symbols, upserted_prices=upserted_prices)
        except EODHDError as e:
            raise UpstreamError(f"EODHD sync failed: {e}")

    def get_latest(self, symbol: str) -> dict[str, Any] | None:
        return self.prices.find_one({"symbol": symbol}, sort=[("date", -1)], projection={"_id": 0})

    def get_history(self, symbol: str, from_date: str | None = None, to_date: str | None = None, limit: int = 400):
        q: dict[str, Any] = {"symbol": symbol}
        if from_date or to_date:
            q["date"] = {}
            if from_date:
                q["date"]["$gte"] = from_date
            if to_date:
                q["date"]["$lte"] = to_date
        cur = self.prices.find(q, projection={"_id": 0}).sort("date", 1).limit(int(limit))
        return list(cur)

    def build_context(self, symbol: str, lookback_days: int = 60) -> str:
        docs = list(
            self.prices.find({"symbol": symbol}, projection={"_id": 0})
            .sort("date", -1)
            .limit(int(lookback_days) + 1)
        )
        if not docs:
            return f"[STOCK_DATA] No data for {symbol}."

        latest = docs[0]
        prev = docs[1] if len(docs) > 1 else None

        date = latest.get("date") or _iso_today()
        close = latest.get("close")
        adj = latest.get("adjusted_close")
        vol = latest.get("volume")
        open_ = latest.get("open")
        high = latest.get("high")
        low = latest.get("low")

        prev_close = prev.get("close") if prev else None
        day_change = None
        day_change_pct = None
        if close is not None and prev_close not in (None, 0):
            try:
                day_change = float(close) - float(prev_close)
                day_change_pct = (day_change / float(prev_close)) * 100.0
            except Exception:
                day_change = None
                day_change_pct = None

        returns_lines: list[str] = []
        horizons = [5, 20, 60]
        for n in horizons:
            if len(docs) > n:
                base_close = docs[n].get("close")
                if close is not None and base_close not in (None, 0):
                    try:
                        ret = (float(close) / float(base_close) - 1.0) * 100.0
                        returns_lines.append(f"{n}d: {ret:+.2f}%")
                    except Exception:
                        pass

        lines: list[str] = []
        lines.append("[STOCK_DATA]")
        lines.append(f"symbol: {symbol}")
        lines.append(f"as_of: {date}")
        lines.append(f"open: {open_}")
        lines.append(f"high: {high}")
        lines.append(f"low: {low}")
        lines.append(f"close: {close}")
        lines.append(f"adjusted_close: {adj}")
        lines.append(f"volume: {vol}")
        if prev_close is not None:
            lines.append(f"prev_close: {prev_close}")
        if day_change is not None:
            lines.append(f"day_change: {day_change:+.4f}")
        if day_change_pct is not None:
            lines.append(f"day_change_pct: {day_change_pct:+.2f}%")
        if returns_lines:
            lines.append("returns:")
            for rline in returns_lines:
                lines.append(f"- {rline}")
        return "\n".join(lines) + "\n"

    def build_universe_top_context(self, limit: int = 20) -> str:
        cur = (
            self.universe.find({}, projection={"_id": 0})
            .sort([("market_capitalization", -1), ("MarketCapitalization", -1)])
            .limit(int(limit))
        )
        lines: list[str] = []
        lines.append("[UNIVERSE_TOP]")
        rank = 0
        for doc in cur:
            rank += 1
            symbol = doc.get("symbol")
            if not symbol:
                code = doc.get("code") or doc.get("Code")
                exch = doc.get("exchange") or doc.get("Exchange")
                if code and exch:
                    symbol = f"{code}.{str(exch).upper()}"
            name = doc.get("name") or doc.get("Name")
            mc = doc.get("market_capitalization")
            if mc is None:
                mc = doc.get("MarketCapitalization")
            lines.append(f"{rank}. {symbol} | name: {name} | market_cap: {mc}")
        return "\n".join(lines) + "\n"

    def extract_symbols_from_text(self, text: str, default_exchange: str = "US") -> list[str]:
        if not text:
            return []

        exchange = (default_exchange or "US").upper()

        cleaned_chars: list[str] = []
        for ch in text:
            if ch.isalnum() or ch == "." or ch == "$" or ch == "-":
                cleaned_chars.append(ch)
            else:
                cleaned_chars.append(" ")
        tokens = "".join(cleaned_chars).split()

        candidates: list[str] = []
        seen: set[str] = set()

        for token in tokens:
            if not token:
                continue
            if token.startswith("$"):
                token = token[1:]
            token = token.strip().upper()
            if not token:
                continue
            if len(token) > 15:
                continue

            has_letter = False
            for ch in token:
                if ch.isalpha():
                    has_letter = True
                    break
            if not has_letter:
                continue

            variants: list[str] = []
            if token.endswith("." + exchange):
                variants.append(token)
            else:
                if "." in token:
                    variants.append(token)
                    variants.append(token.replace(".", "-") + "." + exchange)
                else:
                    variants.append(token + "." + exchange)

            for symbol in variants:
                if symbol not in seen:
                    seen.add(symbol)
                    candidates.append(symbol)

        if not candidates:
            return []

        existing: set[str] = set()
        cur = self.prices.find({"symbol": {"$in": candidates}}, projection={"symbol": 1})
        for doc in cur:
            sym = doc.get("symbol")
            if sym:
                existing.add(sym)

        out: list[str] = []
        for sym in candidates:
            if sym in existing:
                out.append(sym)
        return out

    def build_auto_context(self, user_text: str, default_exchange: str = "US") -> str:
        text = user_text or ""
        lower = text.lower()

        symbols = self.extract_symbols_from_text(text, default_exchange=default_exchange)
        if symbols:
            lines: list[str] = []
            max_symbols = 3
            count = 0
            for sym in symbols:
                count += 1
                if count > max_symbols:
                    break
                lines.append(self.build_context(sym))
            return "\n".join(lines).strip() + "\n"

        wants_top = False
        if "top" in lower:
            wants_top = True
        if "market cap" in lower or "marketcap" in lower:
            wants_top = True

        if wants_top:
            top_n = 20
            idx = lower.find("top")
            if idx != -1:
                after = lower[idx + 3 :]
                pos = 0
                while pos < len(after) and after[pos].isspace():
                    pos += 1

                digits = ""
                while pos < len(after) and after[pos].isdigit():
                    digits += after[pos]
                    pos += 1

                if digits:
                    try:
                        top_n = int(digits)
                    except Exception:
                        top_n = 20
            return self.build_universe_top_context(limit=top_n)

        return ""
