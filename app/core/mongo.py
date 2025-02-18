import os
from dataclasses import dataclass

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from app.core.config import MongoConfig


@dataclass(frozen=True)
class MongoStore:
    client: MongoClient
    db: Database

    @classmethod
    def from_config(cls, cfg: MongoConfig) -> "MongoStore":
        uri = os.getenv(cfg.uri_env) or cfg.uri
        client = MongoClient(uri)
        db = client[cfg.database]
        store = cls(client=client, db=db)
        store._ensure_indexes()
        return store

    def _ensure_indexes(self) -> None:
        prices = self.db["prices_daily"]
        prices.create_index([("symbol", ASCENDING), ("date", ASCENDING)], unique=True)
        prices.create_index([("symbol", ASCENDING), ("date", DESCENDING)])

        universe = self.db["universe"]
        universe.create_index([("exchange", ASCENDING), ("code", ASCENDING)], unique=True)
        universe.create_index([("market_capitalization", DESCENDING)])

        news = self.db["news"]
        news.create_index([("symbol", ASCENDING), ("date", DESCENDING)])
        news.create_index([("symbol", ASCENDING), ("url", ASCENDING)], unique=True, sparse=True)
        news.create_index("fetched_at", expireAfterSeconds=60 * 60 * 24 * 30)
