import pytest
import pytest_asyncio

from mock import patch
from fastapi import FastAPI
from httpx import AsyncClient

from models.domain.authentication import User


@pytest.fixture(autouse=True, scope="module")
def no_lifespan_events():
    with patch("main.lifespan"):
        yield


@pytest.fixture(autouse=True)
def no_auth_token():
    """Overrides validating and decoding tokens for all tests"""
    with patch(
        "services.aad_authentication.AccessService.__call__",
        return_value="token",
    ):
        with patch(
            "services.aad_authentication.AzureADAuthorization._decode_token",
            return_value="decoded_token",
        ):
            yield


@pytest.fixture(autouse=True, scope="session")
def patch_user_management_enabled():
    with patch("core.config.USER_MANAGEMENT_ENABLED", new=True):
        yield


def create_test_user() -> User:
    return User(
        id="user-guid-here",
        name="Test User",
        email="test@user.com",
        roles=[],
        roleAssignments=[],
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


@pytest.fixture(scope="module")
def admin_user():
    return create_admin_user


@pytest.fixture(scope="module")
def non_admin_user():
    return create_non_admin_user


@pytest.fixture(scope="module")
def owner_user():
    return create_workspace_owner_user


@pytest.fixture(scope="module")
def researcher_user():
    return create_workspace_researcher_user


@pytest.fixture(scope="module")
def airlock_manager_user():
    return create_workspace_airlock_manager_user


@pytest.fixture(scope="module")
def no_workspace_role_user():
    def inner():
        return create_test_user()
    return inner


@pytest.fixture(scope="module")
def app() -> FastAPI:
    from main import get_application
    return get_application()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(
        app=app,
        base_url="http://testserver",
        headers={"Content-Type": "application/json"},
    ) as client:
        yield client
