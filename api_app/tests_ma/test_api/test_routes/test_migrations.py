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
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestMigrationRoutesThatRequireAdminRights:
    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, admin_user):
        with patch('services.aad_authentication.AzureADAuthorization._get_user_from_token', return_value=admin_user()):
            app.dependency_overrides[get_current_tre_user_or_tre_admin] = admin_user
            app.dependency_overrides[get_current_admin_user] = admin_user
            yield
            app.dependency_overrides = {}

    # [POST] /migrations/
    @ patch("api.routes.migrations.logger.info")
    @ patch("api.routes.migrations.OperationRepository")
    @ patch("api.routes.migrations.ResourceMigration.archive_history")
    @ patch("api.routes.migrations.ResourceMigration.add_deployment_status_field")
    @ patch("api.routes.migrations.ResourceRepository.rename_field_name")
    @ patch("api.routes.migrations.SharedServiceMigration.deleteDuplicatedSharedServices")
    @ patch("api.routes.migrations.WorkspaceMigration.moveAuthInformationToProperties")
    @ patch("api.routes.migrations.SharedServiceMigration.checkMinFirewallVersion")
    @ patch("api.routes.migrations.AirlockMigration.add_created_by_and_rename_in_history")
    @ patch("api.routes.migrations.AirlockMigration.rename_field_name")
    @ patch("api.routes.migrations.AirlockMigration.change_review_resources_to_dict")
    @ patch("api.routes.migrations.AirlockMigration.update_review_decision_values")
    @ patch("api.routes.migrations.ResourceMigration.add_unique_identifier_suffix")
    async def test_post_migrations_returns_202_on_successful(self, add_unique_identifier_suffix, update_review_decision_values,
                                                             change_review_resources_to_dict, airlock_rename_field, add_created_by_and_rename_in_history,
                                                             check_min_firewall_version, workspace_migration, shared_services_migration, rename_field,
                                                             add_deployment_field, archive_history, _, logging, client, app):
        response = await client.post(app.url_path_for(strings.API_MIGRATE_DATABASE))
        check_min_firewall_version.assert_called_once()
        shared_services_migration.assert_called_once()
        workspace_migration.assert_called_once()
        rename_field.assert_called()
        add_deployment_field.assert_called()
        add_created_by_and_rename_in_history.assert_called_once()
        airlock_rename_field.assert_called()
        change_review_resources_to_dict.assert_called_once()
        update_review_decision_values.assert_called_once()
        migrate_step_id_of_operation_steps.assert_called_once()
        archive_history.assert_called_once()
        add_unique_identifier_suffix.assert_called_once()
        logging.assert_called()
        assert response.status_code == status.HTTP_202_ACCEPTED

    # [POST] /migrations/
    @ patch("api.routes.migrations.logger.info")
    @ patch("api.routes.migrations.ResourceRepository.rename_field_name", side_effect=ValueError)
    @ patch("api.routes.migrations.SharedServiceMigration.deleteDuplicatedSharedServices")
    @ patch("api.routes.migrations.WorkspaceMigration.moveAuthInformationToProperties")
    @ patch("api.routes.migrations.AirlockMigration.add_created_by_and_rename_in_history")
    async def test_post_migrations_returns_400_if_template_does_not_exist(self, workspace_migration, shared_services_migration,
                                                                          resources_repo, airlock_migration, logging, client, app):
        response = await client.post(app.url_path_for(strings.API_MIGRATE_DATABASE))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
