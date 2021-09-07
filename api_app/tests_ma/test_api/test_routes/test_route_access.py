import pytest

from fastapi import status

from api.routes.workspaces import get_current_user
from resources import strings


pytestmark = pytest.mark.asyncio


# TEMPLATES
class TestTemplateRoutesThatRequireAdminRights:
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_non_admin(self, app, non_admin_user):
        # try accessing the route with a non-admin user
        app.dependency_overrides[get_current_user] = non_admin_user
        yield
        app.dependency_overrides = {}

    async def test_get_workspace_templates_requires_admin_rights(self, app, client):
        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_TEMPLATES))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_post_workspace_templates_requires_admin_rights(self, app, client):
        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES), json='{}')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_post_workspace_service_templates_requires_admin_rights(self, app, client):
        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES), json='{}')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_post_user_resource_templates_requires_admin_rights(self, app, client):
        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE_TEMPLATES, service_template_name="not-important"), json='{}')
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_workspace_service_templates_requires_user_rights():
    assert False


def test_get_user_resource_templates_requires_user_rights():
    assert False

# RESOURCES
