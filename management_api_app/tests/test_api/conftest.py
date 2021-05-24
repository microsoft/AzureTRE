import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from asgi_lifespan import LifespanManager


@pytest.fixture
def app() -> FastAPI:
    from main import get_application
    return get_application()


@pytest.fixture
async def initialized_app(app: FastAPI) -> FastAPI:
    async with LifespanManager(app):
        yield app


@pytest.fixture
async def client(initialized_app: FastAPI) -> AsyncClient:
    async with AsyncClient(app=initialized_app, base_url="http://testserver", headers={"Content-Type": "application/json"}) as client:
        yield client
