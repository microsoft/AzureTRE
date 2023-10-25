import pytest
import pytest_asyncio
from mock import patch

from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient

from models.domain.authentication import User


@pytest_asyncio.fixture(autouse=True)
def no_database():
    """ overrides connecting to the database for all tests"""
    with patch('api.dependencies.database.connect_to_db', return_value=None):
        with patch('api.dependencies.database.get_db_client', return_value=None):
            with patch('db.repositories.base.BaseRepository._get_container', return_value=None):
                with patch('db.events.bootstrap_database', return_value=None):
                    yield


@pytest.fixture(autouse=True)
def no_auth_token():
    """ overrides validating and decoding tokens for all tests"""
    with patch('services.aad_authentication.AccessService.__call__', return_value="token"):
        with patch('services.aad_authentication.AzureADAuthorization._decode_token', return_value="decoded_token"):
            yield


def create_test_user() -> User:
    return User(
        id="user-guid-here",
        name="Test User",
        email="test@user.com",
        roles=[],
        roleAssignments=[]
    )


def create_admin_user() -> User:
    user = create_test_user()
    user.roles = ["TREAdmin"]
    user.roleAssignments = [("ab123", "ab124")]
    return user


def create_non_admin_user() -> User:
    user = create_test_user()
    user.roles = ["TREUser"]
    user.roleAssignments = [("ab123", "ab124")]
    return user


def create_workspace_owner_user() -> User:
    user = create_test_user()
    user.roles = ["WorkspaceOwner"]
    return user


def create_workspace_researcher_user() -> User:
    user = create_test_user()
    user.roles = ["WorkspaceResearcher"]
    return user


def create_workspace_airlock_manager_user() -> User:
    user = create_test_user()
    user.roles = ["AirlockManager"]
    return user


def override_get_user():
    user = create_test_user()
    user.roles = []
    user.roleAssignments = [("ab123", "ab124")]
    return user


def get_required_roles(endpoint):
    dependencies = list(filter(lambda x: hasattr(x.dependency, 'require_one_of_roles'), endpoint.__defaults__))
    required_roles = dependencies[0].dependency.require_one_of_roles
    return required_roles


@pytest.fixture(scope='module')
def admin_user():
    def inner():
        return create_admin_user()
    return inner


@pytest.fixture(scope='module')
def non_admin_user():
    def inner():
        return create_non_admin_user()
    return inner


@pytest.fixture(scope='module')
def owner_user():
    def inner():
        return create_workspace_owner_user()
    return inner


@pytest.fixture(scope='module')
def researcher_user():
    def inner():
        return create_workspace_researcher_user()
    return inner


@pytest.fixture(scope='module')
def airlock_manager_user():
    def inner():
        return create_workspace_airlock_manager_user()
    return inner


@pytest.fixture(scope='module')
def no_workspace_role_user():
    def inner():
        user = create_test_user()
        return user
    return inner


@pytest_asyncio.fixture(scope='module')
def app() -> FastAPI:
    from main import get_application

    the_app = get_application()
    return the_app


@pytest_asyncio.fixture
async def initialized_app(app: FastAPI) -> FastAPI:
    async with LifespanManager(app):
        yield app


@pytest_asyncio.fixture
async def client(initialized_app: FastAPI) -> AsyncClient:
    async with AsyncClient(app=initialized_app, base_url="http://testserver", headers={"Content-Type": "application/json"}) as client:
        yield client
