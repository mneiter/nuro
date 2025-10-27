from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from .api import api_router
from .core.config import settings
from .utils.redis import create_redis_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis: Redis | None = None
    try:
        redis = await create_redis_pool(settings.redis_url)
        app.state.redis = redis
        yield
    finally:
        if redis is not None:
            await redis.close()
            await redis.connection_pool.disconnect()


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(api_router, prefix=settings.api_v1_prefix)

    return application


app = create_app()
