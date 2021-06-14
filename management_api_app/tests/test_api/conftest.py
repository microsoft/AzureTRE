import pytest
from mock import patch

from fastapi import FastAPI
from httpx import AsyncClient
from asgi_lifespan import LifespanManager


@pytest.fixture(autouse=True)
def no_database():
    """ overrides connecting to the database for all tests"""
    with patch('api.dependencies.database.connect_to_db', return_value=None):
        with patch('api.dependencies.database.get_db_client', return_value=None):
            with patch('db.repositories.base.BaseRepository._get_container', return_value=None):
                with patch('core.events.bootstrap_database', return_value=None):
                    yield


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
