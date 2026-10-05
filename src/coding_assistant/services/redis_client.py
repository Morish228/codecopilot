import json
import logging
from typing import Any

import redis.asyncio as redis

from coding_assistant.config import get_settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None
_local_memory_cache: dict[str, str] = {}
_redis_disabled = False

RUN_STATE_PREFIX = "run:state:"
RUN_STATE_TTL_SECONDS = 86400


async def get_redis() -> redis.Redis | None:
    global _client, _redis_disabled
    if _redis_disabled:
        return None
    if _client is None:
        settings = get_settings()
        try:
            _client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=1.0,
            )
        except Exception:
            _redis_disabled = True
            return None
    return _client


async def cache_run_state(run_id: str, state: dict[str, Any]) -> None:
    data = json.dumps(state, default=str)
    try:
        client = await get_redis()
        if client:
            await client.setex(
                f"{RUN_STATE_PREFIX}{run_id}",
                RUN_STATE_TTL_SECONDS,
                data,
            )
            return
    except Exception:
        pass
    _local_memory_cache[f"{RUN_STATE_PREFIX}{run_id}"] = data


async def get_cached_run_state(run_id: str) -> dict[str, Any] | None:
    try:
        client = await get_redis()
        if client:
            raw = await client.get(f"{RUN_STATE_PREFIX}{run_id}")
            if raw is not None:
                return json.loads(raw)
    except Exception:
        pass
    raw = _local_memory_cache.get(f"{RUN_STATE_PREFIX}{run_id}")
    if raw is None:
        return None
    return json.loads(raw)


async def delete_cached_run_state(run_id: str) -> None:
    try:
        client = await get_redis()
        if client:
            await client.delete(f"{RUN_STATE_PREFIX}{run_id}")
    except Exception:
        pass
    _local_memory_cache.pop(f"{RUN_STATE_PREFIX}{run_id}", None)
