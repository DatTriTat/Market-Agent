import json
from dataclasses import dataclass
from typing import Any, Iterable

import requests


class EODHDError(RuntimeError):
    pass


@dataclass(frozen=True)
class EODHDClient:
    api_token: str
    base_url: str = "https://eodhd.com/api"

    def _build_url(self, path: str) -> str:
        base = self.base_url
        if base.endswith("/"):
            base = base[:-1]
        return base + "/" + path.lstrip("/")

    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = self._build_url(path)

        final_params: dict[str, Any] = {}
        if params:
            for key, value in params.items():
                if value is None:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                final_params[key] = value

        try:
            resp = requests.get(url, params=final_params, timeout=60)
        except Exception as e:
            raise EODHDError(f"EODHD request failed: {e}")

        if resp.status_code != 200:
            snippet = (resp.text or "")[:300].replace("\n", " ")
            raise EODHDError(f"EODHD HTTP {resp.status_code}. Body: {snippet}")

        try:
            return resp.json()
        except Exception as e:
            snippet = (resp.text or "")[:300].replace("\n", " ")
            raise EODHDError(f"Invalid JSON from EODHD: {e}. Body: {snippet}")

    def exchanges_list(self) -> list[dict[str, Any]]:
        params = {
            "api_token": self.api_token,
            "fmt": "json",
        }
        data = self._get_json("exchanges-list/", params=params)
        if isinstance(data, list):
            return data
        raise EODHDError("Unexpected response for exchanges-list")

    def exchange_symbol_list(self, exchange_code: str) -> list[dict[str, Any]]:
        params = {
            "api_token": self.api_token,
            "fmt": "json",
        }
        data = self._get_json(f"exchange-symbol-list/{exchange_code}", params=params)
        if isinstance(data, list):
            return data
        raise EODHDError("Unexpected response for exchange-symbol-list")

    def screener(self, filters: Iterable[list[Any]], sort: str = "market_capitalization.desc", limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        params = {
            "api_token": self.api_token,
            "sort": sort,
            "filters": json.dumps(list(filters), separators=(",", ":")),
            "limit": int(limit),
            "offset": int(offset),
            "fmt": "json",
        }
        data = self._get_json("screener", params=params)
        if isinstance(data, list):
            return data
        raise EODHDError("Unexpected response for screener")

    def eod(self, symbol: str, from_date: str | None = None, to_date: str | None = None, period: str = "d", order: str = "a") -> list[dict[str, Any]]:
        params = {
            "api_token": self.api_token,
            "fmt": "json",
            "from": from_date,
            "to": to_date,
            "period": period,
            "order": order,
        }
        data = self._get_json(f"eod/{symbol}", params=params)
        if isinstance(data, list):
            return data
        raise EODHDError("Unexpected response for eod")

    def eod_bulk_last_day(self, exchange_code: str) -> list[dict[str, Any]]:
        params = {
            "api_token": self.api_token,
            "fmt": "json",
        }
        data = self._get_json(f"eod-bulk-last-day/{exchange_code}", params=params)
        if isinstance(data, list):
            return data
        raise EODHDError("Unexpected response for eod-bulk-last-day")

    def news(
        self,
        symbol: str | None = None,
        topic: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        params = {
            "api_token": self.api_token,
            "fmt": "json",
            "s": symbol,
            "t": topic,
            "from": from_date,
            "to": to_date,
            "limit": int(limit),
            "offset": int(offset),
        }
        data = self._get_json("news", params=params)
        if isinstance(data, list):
            return data
        raise EODHDError("Unexpected response for news")
