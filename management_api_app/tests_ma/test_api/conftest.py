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


def override_get_user():
    from services.authentication import User
    return User(id="1234", name="test", email="test", roles=[""], roleAssignments={"ab123": "ab124"})


@pytest.fixture(scope='module')
def admin_user():
    def inner():
        from services.authentication import User
        return User(id="1234", name="test", email="test", roles=["TREAdmin"], roleAssignments={"ab123": "ab124"})
    return inner


@pytest.fixture(scope='module')
def app() -> FastAPI:
    from main import get_application
    from api.routes.workspaces import get_current_user

    the_app = get_application()
    the_app.dependency_overrides[get_current_user] = override_get_user
    return the_app


@pytest.fixture
async def initialized_app(app: FastAPI) -> FastAPI:
    async with LifespanManager(app):
        yield app


@pytest.fixture
async def client(initialized_app: FastAPI) -> AsyncClient:
    async with AsyncClient(app=initialized_app, base_url="http://testserver", headers={"Content-Type": "application/json"}) as client:
        yield client
