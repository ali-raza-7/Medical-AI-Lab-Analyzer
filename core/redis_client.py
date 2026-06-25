import os
import logging
import redis as redis_module

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client: redis_module.Redis | None = None

def get_redis() -> redis_module.Redis | None:
    global redis_client
    if redis_client is not None:
        try:
            redis_client.ping()
            return redis_client
        except Exception:
            pass
    try:
        redis_client = redis_module.from_url(REDIS_URL, socket_connect_timeout=3, decode_responses=True)
        redis_client.ping()
        logger.info("[redis] connected at %s", REDIS_URL)
        return redis_client
    except Exception as exc:
        logger.warning("[redis] not available: %s", exc)
        redis_client = None
        return None


def close_redis():
    global redis_client
    if redis_client is not None:
        try:
            redis_client.close()
        except Exception:
            pass
        redis_client = None
