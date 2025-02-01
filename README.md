# Conversation Agent API (FastAPI)

## Setup

```bash
pip install -r requirements.txt
```

Set your key (recommended):

- Windows PowerShell: `setx OPENAI_API_KEY "YOUR_KEY"`
- Or put it in `config.yaml` under `openai.api_key`

Run Redis (required for session cache):

- Docker: `docker run --rm -p 6379:6379 redis:7-alpine`
- Or set `REDIS_URL` to your Redis instance (defaults to `redis://localhost:6379/0`)

Run MongoDB (required for stock data storage):

- Docker: `docker run --rm -p 27017:27017 mongo:7`
- Or set `MONGODB_URI` (defaults to `mongodb://localhost:27017`)

EODHD (required to sync stock data):

- Set `EODHD_API_TOKEN` in your environment (do **not** commit your token).

## Run

```bash
python main.py
```

Base URL: `http://localhost:8000`

Health check: `GET http://localhost:8000/health`

## API

### `POST /api/chat`

Follow-up works by reusing the same `session_id` (history is stored in Redis per session).
If MongoDB stock data is configured, the agent can call stock tools (LangChain) to fetch `[STOCK_DATA]` / `[UNIVERSE_TOP]` from the DB as needed.
If EODHD is configured, the agent can call the news tool to fetch `[STOCK_NEWS]`.
News is cached for 24 hours and stored in MongoDB for 30 days.

Request:

```json
{
  "session_id": "abc123",
  "message": "Hello!",
  "context": null,
  "reset": false
}
```

`reset: true` clears the cached session before replying (starts a new chat thread).

Response:

```json
{
  "session_id": "abc123",
  "reply": "Hi! How can I help you today?",
  "history": [
    { "role": "user", "content": "Hello!" },
    { "role": "assistant", "content": "Hi! How can I help you today?" }
  ]
}
```

Example (Windows `cmd.exe`):

```bat
curl -X POST http://localhost:8000/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\":\"abc123\",\"message\":\"Hello!\",\"context\":null,\"reset\":false}"
```

### `DELETE /api/chat/{session_id}`

Clears the cached conversation for that session.

Example:

```bat
curl -X DELETE http://localhost:8000/api/chat/abc123
```

### `GET /api/chat/{session_id}`

Returns the current cached history for that session.

Example:

```bat
curl http://localhost:8000/api/chat/abc123
```

## Frontend Notes

- Generate `session_id` once per user (e.g., UUID) and store it in `localStorage` so follow-up works.
- If you create a new `session_id` every request, the backend treats it as a new conversation.

## Stocks (EODHD + MongoDB)

### `POST /api/stocks/sync/top`

Fetches top symbols by `market_capitalization` (via EODHD screener) and stores EOD data in MongoDB.

```json
{
  "exchange": "us",
  "limit": 20,
  "min_market_cap": 2000000000,
  "from_date": "2024-01-01",
  "to_date": null,
  "period": "d"
}
```

### `POST /api/stocks/sync/bulk-last-day`

Fetches bulk EOD for the last day (EODHD bulk endpoint) and upserts into MongoDB.

```json
{ "exchange_code": "US", "symbols": ["AAPL.US", "MSFT.US"] }
```

If `symbols` is `null`, it uses the stored universe top-N (`limit` defaults to 20):

```json
{ "exchange_code": "US", "symbols": null, "limit": 20 }
```

### `GET /api/stocks/universe/top?limit=20`

Returns the stored top-universe documents.

### `POST /api/stocks/sync/symbols`

Syncs EOD data for a specific list of symbols (works on free EODHD plans).

```json
{
  "symbols": ["AAPL.US", "MSFT.US"],
  "default_exchange": "US",
  "from_date": "2024-01-01",
  "to_date": null,
  "period": "d"
}
```

### `GET /api/stocks/{symbol}/latest`

Returns latest stored EOD bar for the symbol.

### `GET /api/stocks/{symbol}/history?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD&limit=400`

Returns stored EOD history for the symbol.

### `GET /api/stocks/{symbol}/context`

Returns a short text block you can pass into `POST /api/chat` as `context`.
