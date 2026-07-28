import pytest
import pytest_asyncio
from mock import patch

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from models.domain.authentication import User


@pytest.fixture(autouse=True, scope='module')
def no_lifespan_events():
    with patch("main.lifespan"):
        yield


@pytest.fixture(autouse=True)
def no_auth_token():
    """ overrides validating and decoding tokens for all tests"""
    from auth.models import AuthenticatedUser
    from fastapi.security import HTTPAuthorizationCredentials
    from mock import AsyncMock, MagicMock

    fake_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")

    default_validated = AuthenticatedUser(id="test-user", name="Test User", roles=["TREAdmin"])
    mock_validator = MagicMock()
    mock_validator.validate.return_value = default_validated

    with patch('fastapi.security.HTTPBearer.__call__', new=AsyncMock(return_value=fake_credentials)):
        with patch('auth.dependencies.get_core_validator', return_value=mock_validator):
            with patch('auth.rbac.get_core_validator', return_value=mock_validator):
                with patch('auth.rbac.get_workspace_validator', return_value=mock_validator):
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
    defaults = endpoint.__defaults__ or ()
    dependencies = list(filter(lambda x: hasattr(x.dependency, 'require_one_of_roles'), defaults))
    if dependencies:
        return dependencies[0].dependency.require_one_of_roles
    # New-style deps: check for _role_names attribute on the closure
    dependencies = list(filter(lambda x: hasattr(x.dependency, '_role_names'), defaults))
    if dependencies:
        return dependencies[0].dependency._role_names
    return []


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
async def client(app: FastAPI) -> AsyncClient:

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver", headers={"Content-Type": "application/json"}) as client:
        yield client
