"""Redis-backed rate limiting per organization."""

from coding_assistant.config import get_settings
from coding_assistant.services.redis_client import get_redis


class RateLimitExceeded(Exception):
    def __init__(self, org_id: str, limit: int) -> None:
        super().__init__(f"Rate limit exceeded for org {org_id} (limit={limit}/min)")
        self.org_id = org_id
        self.limit = limit


async def check_rate_limit(org_id: str) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return

    try:
        client = await get_redis()
        if client is None:
            return
        key = f"ratelimit:org:{org_id}"
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, 60)
        if count > settings.rate_limit_per_minute:
            raise RateLimitExceeded(org_id, settings.rate_limit_per_minute)
    except Exception as exc:
        if isinstance(exc, RateLimitExceeded):
            raise
        pass
