import asyncio
from collections.abc import AsyncIterator

import fakeredis.aioredis
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.deps import get_redis_connection, get_session
from app.core.config import settings
from app.db import Base
from app.main import create_app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:?cache=shared"


@pytest.fixture(scope="session")
def event_loop() -> AsyncIterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"uri": True},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def clean_database(db_engine: AsyncEngine) -> AsyncIterator[None]:
    async with db_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            await connection.execute(table.delete())
    yield


@pytest.fixture
async def fakeredis_client() -> AsyncIterator[fakeredis.aioredis.FakeRedis]:
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await redis.flushall()
    try:
        yield redis
    finally:
        await redis.flushall()
        close = getattr(redis, "close", None)
        if callable(close):
            await close()


@pytest.fixture
async def app(
    session_factory: async_sessionmaker[AsyncSession],
    fakeredis_client: fakeredis.aioredis.FakeRedis,
):
    application = create_app()
    settings.environment = "test"
    settings.rate_limit_tokens = 1000
    settings.rate_limit_period_seconds = 1
    application.state.redis = fakeredis_client

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def override_redis() -> fakeredis.aioredis.FakeRedis:
        return fakeredis_client

    application.dependency_overrides[get_session] = override_session
    application.dependency_overrides[get_redis_connection] = override_redis
    try:
        yield application
    finally:
        application.dependency_overrides.clear()


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(app=app, base_url="http://testserver/api") as test_client:
        yield test_client
