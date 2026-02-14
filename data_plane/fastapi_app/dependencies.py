from fastapi import HTTPException, Request


async def get_api_key(request: Request) -> str:
    api_key_header = request.headers.get("X-API-Key")
    if not api_key_header:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    return api_key_header
