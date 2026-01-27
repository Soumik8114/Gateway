import hashlib
import time
import os
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import Response
import httpx
from sqlalchemy import MetaData, Table, Column, Integer, String, Boolean, ForeignKey
from databases import Database
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#DB setup
DEFAULT_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../control_plane/db.sqlite3"))
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH}"

DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

logger.info(f"Connecting to database at {DATABASE_URL}")

database = Database(DATABASE_URL)
metadata = MetaData()

tenants_tenant = Table(
    "tenants_tenant",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("slug", String),
    Column("is_active", Boolean),
)

apis_api = Table(
    "apis_api",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tenant_id", Integer, ForeignKey("tenants_tenant.id")),
    Column("slug", String),
    Column("upstream_base_url", String),
    Column("is_active", Boolean),
)

billing_plan = Table(
    "billing_plan",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("requests_per_minute", Integer),
    Column("is_active", Boolean),
)

apis_apikey = Table(
    "apis_apikey",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tenant_id", Integer, ForeignKey("tenants_tenant.id")),
    Column("plan_id", Integer, ForeignKey("billing_plan.id")),
    Column("hashed_key", String),
    Column("is_active", Boolean),
)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = None
http_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()

    global http_client
    http_client = httpx.AsyncClient()

    global redis_client
    try:
        # Try connecting to real redis
        client = redis.from_url(REDIS_URL, decode_responses=True)
        await client.ping()
        logger.info(f"Connected to Redis at {REDIS_URL}")
        redis_client = client
    except (redis.ConnectionError, OSError, ConnectionRefusedError) as e:
        logger.warning(f"Redis not available ({e}), falling back to fakeredis")
        try:
            import fakeredis.aioredis
            redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
        except ImportError:
             # Fallback if aioredis is not available in fakeredis (should be in 2.0+)
             logger.error("fakeredis.aioredis not available!")
             raise e

    try:
        yield
    finally:
        await database.disconnect()
        if redis_client:
            await redis_client.close()
        if http_client:
            await http_client.aclose()

app = FastAPI(lifespan=lifespan)

async def get_api_key(request: Request):
    api_key_header = request.headers.get("X-API-Key")
    if not api_key_header:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    return api_key_header

async def record_usage(tenant_id: int, api_id: int):
    if redis_client:
        current_minute = int(time.time() // 60)
        await redis_client.incr(f"usage:{tenant_id}:{api_id}:{current_minute}")

@app.api_route("/{tenant_slug}/{api_slug}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_request(
    tenant_slug: str,
    api_slug: str,
    path: str,
    request: Request,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(get_api_key)
):
    hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
    # Check Tenant
    query = tenants_tenant.select().where(
        (tenants_tenant.c.slug == tenant_slug) &
        (tenants_tenant.c.is_active == True)
    )
    tenant = await database.fetch_one(query)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Check API
    query = apis_api.select().where(
        (apis_api.c.tenant_id == tenant['id']) &
        (apis_api.c.slug == api_slug) &
        (apis_api.c.is_active == True)
    )
    api = await database.fetch_one(query)
    if not api:
        raise HTTPException(status_code=404, detail="API not found")

    # Check API Key
    query = apis_apikey.select().where(
        (apis_apikey.c.hashed_key == hashed_key) &
        (apis_apikey.c.tenant_id == tenant['id']) &
        (apis_apikey.c.is_active == True)
    )
    key_record = await database.fetch_one(query)

    if not key_record:
        raise HTTPException(status_code=403, detail="Invalid or inactive API Key")

    # Get Plan
    query = billing_plan.select().where(billing_plan.c.id == key_record['plan_id'])
    plan = await database.fetch_one(query)

    if not plan or not plan['is_active']:
         raise HTTPException(status_code=403, detail="Plan invalid")

    # Key: rate_limit:{api_key_id}:{minute_timestamp}
    current_minute = int(time.time() // 60)
    rate_limit_key = f"rate_limit:{key_record['id']}:{current_minute}"

    # Increment and get value
    request_count = await redis_client.incr(rate_limit_key)
    if request_count == 1:
        await redis_client.expire(rate_limit_key, 60) # Expire after 1 minute

    if request_count > plan['requests_per_minute']:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Ensure upstream_base_url doesn't have trailing slash and path doesn't have leading slash duplication
    upstream_base = api['upstream_base_url'].rstrip('/')
    target_path = path.lstrip('/')
    upstream_url = f"{upstream_base}/{target_path}"

    # Construct headers
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    headers.pop("x-api-key", None) # Remove our API key

    try:
        # Use shared client
        body = await request.body()

        response = await http_client.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            content=body,
            params=request.query_params
        )

        # Record Usage (Async/Background)
        background_tasks.add_task(record_usage, tenant['id'], api['id'])

        # Filter response headers
        excluded_headers = {"content-encoding", "content-length", "transfer-encoding", "connection"}
        response_headers = {
            k: v for k, v in response.headers.items()
            if k.lower() not in excluded_headers
        }

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers
        )
    except httpx.RequestError as exc:
        logger.error(f"Upstream request failed: {exc}")
        raise HTTPException(status_code=502, detail="Upstream service unavailable")
