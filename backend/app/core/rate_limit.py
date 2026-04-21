"""Redis-based rate limiter and user status cache helpers.

Used by:
- H4 (`/api/auth/check-user`) + M3 (`/api/auth/login`): shared IP + username rate limit.
- H1 / M1 / M2: user status cache invalidation.
"""
from typing import Optional, Tuple

from app.core.redis import get_redis


# ---------------------------------------------------------------------------
# Rate limit
# ---------------------------------------------------------------------------

# Shared prefixes (used by H4 and M3).
AUTH_IP_RATE_KEY = "rate:auth:ip:{ip}"          # 30 / 60s
AUTH_USER_RATE_KEY_1M = "rate:auth:user:1m:{u}"  # 10 / 60s
AUTH_USER_RATE_KEY_10M = "rate:auth:user:10m:{u}"  # 30 / 600s

AUTH_IP_LIMIT = 30
AUTH_IP_WINDOW = 60
AUTH_USER_1M_LIMIT = 10
AUTH_USER_1M_WINDOW = 60
AUTH_USER_10M_LIMIT = 30
AUTH_USER_10M_WINDOW = 600


async def _incr_with_expire(key: str, window: int) -> int:
    """INCR key; set TTL on first increment; return current count."""
    r = await get_redis()
    n = await r.incr(key)
    if n == 1:
        await r.expire(key, window)
    return int(n)


async def _get_ttl(key: str) -> int:
    r = await get_redis()
    ttl = await r.ttl(key)
    try:
        ttl = int(ttl)
    except Exception:
        ttl = -1
    return ttl if ttl > 0 else 0


async def check_auth_ip_limit(client_ip: str) -> Tuple[bool, int]:
    """Check IP-level rate limit without incrementing.

    Returns (allowed, retry_after_seconds).
    """
    if not client_ip:
        return True, 0
    key = AUTH_IP_RATE_KEY.format(ip=client_ip)
    r = await get_redis()
    val = await r.get(key)
    try:
        current = int(val) if val is not None else 0
    except Exception:
        current = 0
    if current >= AUTH_IP_LIMIT:
        return False, await _get_ttl(key) or AUTH_IP_WINDOW
    return True, 0


async def check_auth_user_limit(username: str) -> Tuple[bool, int]:
    """Check username-level rate limit without incrementing.

    Returns (allowed, retry_after_seconds).
    """
    if not username:
        return True, 0
    r = await get_redis()
    k1 = AUTH_USER_RATE_KEY_1M.format(u=username)
    k10 = AUTH_USER_RATE_KEY_10M.format(u=username)
    v1 = await r.get(k1)
    v10 = await r.get(k10)
    try:
        c1 = int(v1) if v1 is not None else 0
        c10 = int(v10) if v10 is not None else 0
    except Exception:
        c1, c10 = 0, 0
    if c1 >= AUTH_USER_1M_LIMIT:
        return False, await _get_ttl(k1) or AUTH_USER_1M_WINDOW
    if c10 >= AUTH_USER_10M_LIMIT:
        return False, await _get_ttl(k10) or AUTH_USER_10M_WINDOW
    return True, 0


async def record_auth_failure(client_ip: Optional[str], username: Optional[str]) -> None:
    """Increment failure counters for IP + username."""
    if client_ip:
        await _incr_with_expire(AUTH_IP_RATE_KEY.format(ip=client_ip), AUTH_IP_WINDOW)
    if username:
        await _incr_with_expire(AUTH_USER_RATE_KEY_1M.format(u=username), AUTH_USER_1M_WINDOW)
        await _incr_with_expire(AUTH_USER_RATE_KEY_10M.format(u=username), AUTH_USER_10M_WINDOW)


async def reset_auth_counters(client_ip: Optional[str], username: Optional[str]) -> None:
    """Clear counters on successful login."""
    r = await get_redis()
    keys = []
    if client_ip:
        keys.append(AUTH_IP_RATE_KEY.format(ip=client_ip))
    if username:
        keys.append(AUTH_USER_RATE_KEY_1M.format(u=username))
        keys.append(AUTH_USER_RATE_KEY_10M.format(u=username))
    if keys:
        await r.delete(*keys)


# ---------------------------------------------------------------------------
# User status cache (H1)
# ---------------------------------------------------------------------------

USER_STATUS_KEY = "user:status:{uid}"
USER_STATUS_TTL = 45  # seconds


async def get_cached_user_status(user_id: str) -> Optional[dict]:
    r = await get_redis()
    import json
    data = await r.get(USER_STATUS_KEY.format(uid=user_id))
    if data:
        try:
            return json.loads(data)
        except Exception:
            return None
    return None


async def set_cached_user_status(user_id: str, payload: dict) -> None:
    r = await get_redis()
    import json
    await r.setex(
        USER_STATUS_KEY.format(uid=user_id),
        USER_STATUS_TTL,
        json.dumps(payload, default=str),
    )


async def invalidate_user_status(user_id: str) -> None:
    r = await get_redis()
    await r.delete(USER_STATUS_KEY.format(uid=user_id))
