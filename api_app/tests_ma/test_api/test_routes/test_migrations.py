import pytest
from mock import patch

from fastapi import status
from auth.rbac import require_tre_admin, require_tre_user_or_admin
from resources import strings


pytestmark = pytest.mark.asyncio


class TestMigrationRoutesWithNonAdminRights:
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_non_admin_user(self, app, non_admin_user):
        from fastapi import HTTPException

        def forbidden():
            raise HTTPException(status_code=403)
        app.dependency_overrides[require_tre_admin] = forbidden
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
        app.dependency_overrides[require_tre_user_or_admin] = admin_user
        app.dependency_overrides[require_tre_admin] = admin_user
        yield
        app.dependency_overrides = {}

    # [POST] /migrations/
    @patch("api.routes.migrations.WorkspaceRepository.create")
    @patch("api.routes.migrations.logger.info")
    async def test_post_migrations_returns_202_on_successful(self, logging, workspace_repo, client, app):
        workspace_repo.return_value.set_default_airlock_version_for_legacy_workspaces.return_value = []
        response = await client.post(app.url_path_for(strings.API_MIGRATE_DATABASE))

        logging.assert_called()
        if response.status_code != status.HTTP_202_ACCEPTED:
            raise AssertionError(f"Expected status code {status.HTTP_202_ACCEPTED}, but got {response.status_code}")

    # [POST] /migrations/
    @patch("api.routes.migrations.WorkspaceRepository.create")
    @patch("api.routes.migrations.logger.info")
    async def test_post_migrations_stamps_legacy_workspaces_with_v1(self, logging, workspace_repo, client, app):
        # Without this the bundle's v2 default would migrate a pre-v2 workspace on its next deploy.
        workspace_repo.return_value.set_default_airlock_version_for_legacy_workspaces.return_value = ["ws-1", "ws-2"]
        response = await client.post(app.url_path_for(strings.API_MIGRATE_DATABASE))

        workspace_repo.return_value.set_default_airlock_version_for_legacy_workspaces.assert_awaited_once()
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "2 legacy workspace(s)" in response.json()["migrations"][0]["status"]
