import logging

from fastapi import FastAPI

from .lifespan import lifespan
from .proxy import router as proxy_router

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(proxy_router)
    return app


app = create_app()
