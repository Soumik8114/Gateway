import hashlib
import logging
import time

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import Response

from .dependencies import get_api_key
from .tables import apis_api, apis_apikey, apis_client, billing_plan, tenants_tenant
from .usage import record_usage

logger = logging.getLogger(__name__)

router = APIRouter()


@router.api_route(
    "/{tenant_slug}/{api_slug}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
)
async def proxy_request(
    tenant_slug: str,
    api_slug: str,
    path: str,
    request: Request,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(get_api_key),
):
    services = request.app.state.services
    database = services.database
    http_client = services.http_client
    redis_client = services.redis_client

    hashed_key = hashlib.sha256(api_key.encode()).hexdigest()

    # Check Tenant
    query = tenants_tenant.select().where(
        (tenants_tenant.c.slug == tenant_slug) & (tenants_tenant.c.is_active == True)
    )
    tenant = await database.fetch_one(query)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Check API
    query = apis_api.select().where(
        (apis_api.c.tenant_id == tenant["id"]) &
        (apis_api.c.slug == api_slug) &
        (apis_api.c.is_active == True)
    )
    api = await database.fetch_one(query)
    if not api:
        raise HTTPException(status_code=404, detail="API not found")

    # Check API Key
    query = apis_apikey.select().where(
        (apis_apikey.c.hashed_key == hashed_key) &
        (apis_apikey.c.tenant_id == tenant["id"]) &
        (apis_apikey.c.is_active == True)
    )
    key_record = await database.fetch_one(query)

    if not key_record:
        raise HTTPException(status_code=403, detail="Invalid or inactive API Key")

    # Check for X-Client-ID
    client_id = request.headers.get("X-Client-ID")
    active_plan = None
    client_record = None

    if client_id:
        query = apis_client.select().where(
            (apis_client.c.client_id == client_id) &
            (apis_client.c.tenant_id == tenant["id"])
        )
        client_record = await database.fetch_one(query)
        if not client_record:
            raise HTTPException(status_code=403, detail="Invalid Client ID")

        query = billing_plan.select().where(billing_plan.c.id == client_record["plan_id"])
        active_plan = await database.fetch_one(query)

    # Get API Key Plan if no client plan
    if not active_plan:
        query = billing_plan.select().where(billing_plan.c.id == key_record["plan_id"])
        active_plan = await database.fetch_one(query)

    if not active_plan or not active_plan["is_active"]:
        raise HTTPException(status_code=403, detail="Plan invalid")

    # Rate Limiting
    if client_record:
        rate_limit_key_base = f"rate_limit_client:{client_record['id']}"
    else:
        rate_limit_key_base = f"rate_limit:{key_record['id']}"

    # Minute Limit
    current_minute = int(time.time() // 60)
    rate_limit_key_min = f"{rate_limit_key_base}:{current_minute}"

    request_count_min = await redis_client.incr(rate_limit_key_min)
    if request_count_min == 1:
        await redis_client.expire(rate_limit_key_min, 60)

    if request_count_min > active_plan["requests_per_minute"]:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Monthly Limit
    if active_plan["requests_per_month"] is not None:
        current_time = time.gmtime()
        current_month_str = f"{current_time.tm_year}-{current_time.tm_mon}"
        rate_limit_key_month = f"{rate_limit_key_base}:month:{current_month_str}"

        request_count_month = await redis_client.incr(rate_limit_key_month)
        if request_count_month == 1:
            await redis_client.expire(rate_limit_key_month, 60 * 60 * 24 * 32)

        if request_count_month > active_plan["requests_per_month"]:
            raise HTTPException(status_code=429, detail="Monthly rate limit exceeded")

    # Ensure upstream_base_url doesn't have trailing slash and path doesn't have leading slash duplication
    upstream_base = api["upstream_base_url"].rstrip("/")
    target_path = path.lstrip("/")
    upstream_url = f"{upstream_base}/{target_path}"

    # Construct headers
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    headers.pop("x-api-key", None)

    try:
        body = await request.body()
        upstream_response = await http_client.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            content=body,
            params=request.query_params,
        )

        background_tasks.add_task(record_usage, redis_client, tenant["id"], api["id"])

        excluded_headers = {"content-encoding", "content-length", "transfer-encoding", "connection"}
        response_headers = {
            k: v for k, v in upstream_response.headers.items()
            if k.lower() not in excluded_headers
        }

        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            headers=response_headers,
        )
    except httpx.RequestError as exc:
        logger.error(f"Upstream request failed: {exc}")
        raise HTTPException(status_code=502, detail="Upstream service unavailable")
