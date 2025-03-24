from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from redis import Redis


class SessionCache:
    """
    Redis-backed session cache with TTL and max history length.
    """

    def __init__(self, redis_url: str, key_prefix: str, ttl_seconds: int, max_messages: int):
        import redis  # local import so py_compile works without the dependency installed

        self.ttl_seconds = ttl_seconds
        self.max_messages = max_messages
        self.key_prefix = (key_prefix or "").strip(":") or "conv-agent"
        self.redis: "Redis" = redis.Redis.from_url(redis_url, decode_responses=True)

    def ping(self) -> bool:
        return bool(self.redis.ping())

    def _key(self, session_id: str) -> str:
        return f"{self.key_prefix}:session:{session_id}"

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        import json

        key = self._key(session_id)
        items = cast(list[str], self.redis.lrange(key, 0, -1) or [])
        out: list[dict[str, str]] = []
        for raw in items:
            try:
                msg = json.loads(raw)
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    out.append({"role": str(msg["role"]), "content": str(msg["content"])})
            except Exception:
                continue
        return out

    def append(self, session_id: str, role: str, content: str) -> None:
        import json

        if not content:
            return
        key = self._key(session_id)
        payload = json.dumps({"role": role, "content": content}, ensure_ascii=False)
        self.redis.rpush(key, payload)
        self.redis.ltrim(key, -self.max_messages, -1)
        self.redis.expire(key, self.ttl_seconds)

    def reset(self, session_id: str) -> None:
        self.redis.delete(self._key(session_id))
