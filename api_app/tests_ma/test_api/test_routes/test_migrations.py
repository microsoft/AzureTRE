import pytest
from mock import patch

from fastapi import status
from services.authentication import get_current_admin_user, get_current_tre_user_or_tre_admin
from resources import strings


pytestmark = pytest.mark.asyncio


class TestMigrationRoutesWithNonAdminRights:
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_non_admin_user(self, app, non_admin_user):
        with patch('services.aad_authentication.AzureADAuthorization._get_user_from_token', return_value=non_admin_user()):
            app.dependency_overrides[get_current_tre_user_or_tre_admin] = non_admin_user
            yield
            app.dependency_overrides = {}

    # [POST] /migrations/
    async def test_post_migrations_throws_unauthenticated_when_not_admin(self, client, app):
        response = await client.post(app.url_path_for(strings.API_MIGRATE_DATABASE))
        if response.status_code != status.HTTP_403_FORBIDDEN:
            raise AssertionError(f"Expected status code {status.HTTP_403_FORBIDDEN}, but got {response.status_code}")


class TestMigrationRoutesThatRequireAdminRights:
    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, admin_user):
        with patch('services.aad_authentication.AzureADAuthorization._get_user_from_token', return_value=admin_user()):
            app.dependency_overrides[get_current_tre_user_or_tre_admin] = admin_user
            app.dependency_overrides[get_current_admin_user] = admin_user
            yield
            app.dependency_overrides = {}

    # [POST] /migrations/
    @patch("api.routes.migrations.logger.info")
    async def test_post_migrations_returns_202_on_successful(self, logging, client, app):
        response = await client.post(app.url_path_for(strings.API_MIGRATE_DATABASE))

        logging.assert_called()
        if response.status_code != status.HTTP_202_ACCEPTED:
            raise AssertionError(f"Expected status code {status.HTTP_202_ACCEPTED}, but got {response.status_code}")
