# app/db/redis_client.py
import os
import redis.asyncio as redis

# Load Redis URL from environment, fallback to default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create a Redis client instance
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def get_redis():
    """
    Dependency to provide Redis client in FastAPI endpoints
    Usage: `redis: redis.Redis = Depends(get_redis)`
    """
    try:
        yield redis_client
    finally:
        pass  # We Do not close here; we want the client to persist for app lifetime
