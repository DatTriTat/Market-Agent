from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_stocks_service
from app.schemas.stocks import (
    BulkLastDayRequest,
    PriceDoc,
    PriceHistoryResponse,
    SyncTopRequest,
    SyncTopResponse,
    SyncSymbolsRequest,
    SyncSymbolsResponse,
    UniverseItem,
)
from app.services.stocks_service import StocksService

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.post("/sync/top", response_model=SyncTopResponse)
def sync_top(
    payload: SyncTopRequest,
    svc: StocksService = Depends(get_stocks_service),
):
    res = svc.sync_top_eod(
        exchange=payload.exchange,
        limit=payload.limit,
        min_market_cap=payload.min_market_cap,
        from_date=payload.from_date,
        to_date=payload.to_date,
        period=payload.period,
    )
    return SyncTopResponse(
        symbols=res.symbols,
        upserted_prices=res.upserted_prices,
        upserted_universe=res.upserted_universe,
    )


@router.post("/sync/bulk-last-day")
def sync_bulk_last_day(
    payload: BulkLastDayRequest,
    svc: StocksService = Depends(get_stocks_service),
):
    symbols = payload.symbols
    if symbols is None:
        cur = (
            svc.universe.find({}, projection={"_id": 0, "symbol": 1})
            .sort([("market_capitalization", -1), ("MarketCapitalization", -1)])
            .limit(int(payload.limit))
        )
        symbols = []
        for doc in cur:
            sym = doc.get("symbol")
            if sym:
                symbols.append(sym)
    upserted = svc.sync_bulk_last_day(
        exchange_code=payload.exchange_code,
        symbols=symbols,
    )
    return {"upserted": upserted}


@router.post("/sync/symbols", response_model=SyncSymbolsResponse)
def sync_symbols(
    payload: SyncSymbolsRequest,
    svc: StocksService = Depends(get_stocks_service),
):
    res = svc.sync_symbols(
        symbols=payload.symbols,
        default_exchange=payload.default_exchange,
        from_date=payload.from_date,
        to_date=payload.to_date,
        period=payload.period,
    )
    return SyncSymbolsResponse(symbols=res.symbols, upserted_prices=res.upserted_prices)


@router.get("/universe/top", response_model=list[UniverseItem])
def get_universe_top(limit: int = 20, svc: StocksService = Depends(get_stocks_service)):
    cur = (
        svc.universe.find({}, projection={"_id": 0})
        .sort([("market_capitalization", -1), ("MarketCapitalization", -1)])
        .limit(int(limit))
    )
    out: list[UniverseItem] = []
    for doc in cur:
        mc = doc.get("market_capitalization") or doc.get("MarketCapitalization")
        code = doc.get("code") or doc.get("Code")
        out.append(
            UniverseItem(
                symbol=doc.get("symbol")
                or (f"{code}.{str(doc.get('exchange') or '').upper()}" if code else ""),
                exchange=doc.get("exchange"),
                code=code,
                market_capitalization=float(mc) if mc is not None else None,
                raw=doc,
            )
        )
    return out


@router.get("/{symbol}/latest", response_model=PriceDoc)
def get_latest(symbol: str, svc: StocksService = Depends(get_stocks_service)):
    doc = svc.get_latest(symbol)
    if not doc:
        raise HTTPException(status_code=404, detail="symbol not found")
    return doc


@router.get("/{symbol}/history", response_model=PriceHistoryResponse)
def get_history(
    symbol: str,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 400,
    svc: StocksService = Depends(get_stocks_service),
):
    items = svc.get_history(symbol, from_date=from_date, to_date=to_date, limit=limit)
    return PriceHistoryResponse(symbol=symbol, items=items)


@router.get("/{symbol}/context")
def get_context(symbol: str, svc: StocksService = Depends(get_stocks_service)):
    return {"symbol": symbol, "context": svc.build_context(symbol)}
