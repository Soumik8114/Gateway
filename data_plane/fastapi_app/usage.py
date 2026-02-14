import time


async def record_usage(redis_client, tenant_id: int, api_id: int) -> None:
    if not redis_client:
        return
    current_minute = int(time.time() // 60)
    await redis_client.incr(f"usage:{tenant_id}:{api_id}:{current_minute}")
