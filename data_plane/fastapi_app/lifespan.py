import logging
from contextlib import asynccontextmanager

import httpx
from databases import Database
from fastapi import FastAPI
import redis.asyncio as redis

from .config import get_database_url, get_redis_url
from .state import AppState

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database_url = get_database_url()
    logger.info(f"Connecting to database at {database_url}")

    database = Database(database_url)
    await database.connect()

    http_client = httpx.AsyncClient()

    redis_url = get_redis_url()
    try:
        client = redis.from_url(redis_url, decode_responses=True)
        await client.ping()
        logger.info(f"Connected to Redis at {redis_url}")
        redis_client = client
    except (redis.ConnectionError, OSError, ConnectionRefusedError) as e:
        logger.warning(f"Redis not available ({e}), falling back to fakeredis")
        import fakeredis.aioredis

        redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)

    app.state.services = AppState(database=database, http_client=http_client, redis_client=redis_client)

    try:
        yield
    finally:
        await database.disconnect()
        try:
            await redis_client.close()
        except Exception:
            pass
        await http_client.aclose()
