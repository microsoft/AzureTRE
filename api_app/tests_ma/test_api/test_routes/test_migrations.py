import pytest
from mock import AsyncMock, patch

from fastapi import status
from auth.rbac import require_tre_admin, require_tre_user_or_admin
from resources import strings


pytestmark = pytest.mark.asyncio


class TestMigrationRoutesWithNonAdminRights:
    @pytest.fixture(autouse=True, scope="class")
    @classmethod
    def log_in_with_non_admin_user(cls, app, non_admin_user):
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
    @pytest.fixture(autouse=True, scope="class")
    @classmethod
    def _prepare(cls, app, admin_user):
        app.dependency_overrides[require_tre_user_or_admin] = admin_user
        app.dependency_overrides[require_tre_admin] = admin_user
        yield
        app.dependency_overrides = {}

    @pytest.fixture(autouse=True)
    def resource_repo(self):
        with (
            patch("api.routes.migrations.ResourceRepository.create") as resource_repo,
            patch("api.routes.migrations.ResourceTemplateRepository.create"),
            patch("api.routes.migrations.ResourceHistoryRepository.create"),
        ):
            resource_repo.return_value.mask_stored_sensitive_values = AsyncMock(return_value=(0, 0))
            yield resource_repo.return_value

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

    # [POST] /migrations/
    @patch("api.routes.migrations.WorkspaceRepository.create")
    @patch("api.routes.migrations.logger.info")
    async def test_post_migrations_masks_stored_sensitive_values(
        self, logging, workspace_repo, resource_repo, client, app
    ):
        workspace_repo.return_value.set_default_airlock_version_for_legacy_workspaces.return_value = []
        resource_repo.mask_stored_sensitive_values.return_value = (2, 3)
        response = await client.post(app.url_path_for(strings.API_MIGRATE_DATABASE))

        resource_repo.mask_stored_sensitive_values.assert_awaited_once()
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "2 resource(s) and 3 history item(s)" in response.json()["migrations"][1]["status"]
