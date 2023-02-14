import json
import pytest
from mock import patch

from starlette import status

from services.authentication import get_current_admin_user, get_current_tre_user_or_tre_admin
from db.errors import DuplicateEntity, EntityDoesNotExist, EntityVersionExist, InvalidInput, UnableToAccessDatabase
from models.domain.resource import ResourceType
from models.domain.user_resource_template import UserResourceTemplate
from models.schemas.resource_template import ResourceTemplateInformation
from resources import strings

pytestmark = pytest.mark.asyncio


@pytest.fixture
def user_resource_template_without_enriching():
    def create_user_resource_template(template_name: str = "vm-resource-template", parent_service: str = "guacamole-service"):
        return UserResourceTemplate(
            id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
            name=template_name,
            description="vm-bundle",
            version="0.1.0",
            resourceType=ResourceType.UserResource,
            current=True,
            type="object",
            required=[],
            properties={},
            actions=[],
            parentWorkspaceService=parent_service
        )
    return create_user_resource_template


class TestUserResourceTemplatesRequiringAdminRights:
    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, admin_user):
        app.dependency_overrides[get_current_tre_user_or_tre_admin] = admin_user
        app.dependency_overrides[get_current_admin_user] = admin_user
        yield
        app.dependency_overrides = {}

    # POST /workspace-service-templates/{service_template_name}/user-resource-templates
    @patch("api.dependencies.workspace_service_templates.ResourceTemplateRepository.get_current_template", side_effect=EntityDoesNotExist)
    async def test_creating_user_resource_template_raises_404_if_service_template_does_not_exist(self, _, input_user_resource_template, app, client):
        parent_workspace_service_name = "some_template_name"

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE_TEMPLATES, service_template_name=parent_workspace_service_name), json=input_user_resource_template.dict())

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # POST /workspace-service-templates/{template_name}/user-resource-templates
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_and_validate_template")
    @patch("api.dependencies.workspace_service_templates.ResourceTemplateRepository.get_current_template")
    async def test_when_creating_user_resource_template_it_is_returned_as_expected(self, get_current_template_mock, create_template_mock, app, client, input_user_resource_template, basic_workspace_service_template, user_resource_template_in_response):
        get_current_template_mock.return_value = basic_workspace_service_template

        parent_workspace_service_name = "guacamole"
        user_resource_template_in_response.parentWorkspaceService = parent_workspace_service_name
        create_template_mock.return_value = user_resource_template_in_response

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE_TEMPLATES, service_template_name=parent_workspace_service_name), json=input_user_resource_template.dict())

        assert json.loads(response.text)["resourceType"] == ResourceType.UserResource
        assert json.loads(response.text)["parentWorkspaceService"] == parent_workspace_service_name
        assert json.loads(response.text)["name"] == user_resource_template_in_response.name

    # POST /workspace-service-templates/{template_name}/user-resource-templates
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_and_validate_template")
    @patch("api.dependencies.workspace_service_templates.ResourceTemplateRepository.get_current_template")
    async def test_when_creating_user_resource_template_enriched_service_template_is_returned(self, get_current_template_mock, create_template_mock, app, client, input_user_resource_template, basic_workspace_service_template, user_resource_template_in_response):
        get_current_template_mock.return_value = basic_workspace_service_template

        parent_workspace_service_name = "guacamole"
        user_resource_template_in_response.parentWorkspaceService = parent_workspace_service_name
        create_template_mock.return_value = user_resource_template_in_response
        expected_template = user_resource_template_in_response

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE_TEMPLATES, service_template_name=parent_workspace_service_name), json=input_user_resource_template.dict())

        assert json.loads(response.text)["properties"] == expected_template.properties
        assert json.loads(response.text)["required"] == expected_template.required

    # POST /workspace-service-templates/{template_name}/user-resource-templates
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_and_validate_template")
    @patch("api.dependencies.workspace_service_templates.ResourceTemplateRepository.get_current_template")
    async def test_when_creating_user_resource_template_returns_409_if_version_exists(self, get_current_template_mock, create_user_resource_template_mock, app, client, input_user_resource_template, basic_workspace_service_template, user_resource_template_in_response):
        get_current_template_mock.return_value = basic_workspace_service_template

        parent_workspace_service_name = "guacamole"
        create_user_resource_template_mock.side_effect = EntityVersionExist

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE_TEMPLATES, service_template_name=parent_workspace_service_name), json=input_user_resource_template.dict())

        assert response.status_code == status.HTTP_409_CONFLICT

    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_and_validate_template", side_effect=InvalidInput)
    @patch("api.dependencies.workspace_service_templates.ResourceTemplateRepository.get_current_template")
    async def test_creating_a_user_resource_template_raises_http_422_if_step_ids_are_duplicated(self, _, __, client, app, input_user_resource_template):
        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE_TEMPLATES, service_template_name="guacamole"), json=input_user_resource_template.dict())

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserResourceTemplatesNotRequiringAdminRights:
    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, researcher_user):
        app.dependency_overrides[get_current_tre_user_or_tre_admin] = researcher_user
        yield
        app.dependency_overrides = {}

    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_templates_information")
    async def test_get_user_resource_templates_returns_template_names_and_description(self, get_templates_information_mock, app, client):
        expected_templates = [
            ResourceTemplateInformation(name="template1", title="template 1", description="description1"),
            ResourceTemplateInformation(name="template2", title="template 2", description="description2")
        ]
        get_templates_information_mock.return_value = expected_templates

        response = await client.get(app.url_path_for(strings.API_GET_USER_RESOURCE_TEMPLATES, service_template_name="parent_service_name"))

        assert response.status_code == status.HTTP_200_OK
        actual_templates = response.json()["templates"]
        assert len(actual_templates) == len(expected_templates)
        for template in expected_templates:
            assert template in actual_templates

    # GET /workspace-service-templates/{service_template_name}/user-resource-templates/{user_resource_template_name}
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_template")
    async def test_user_resource_templates_by_name_returns_enriched_user_resource_template(self, get_current_template_mock, app, client, user_resource_template_without_enriching):
        service_template_name = "guacamole-service"
        user_resource_template_name = "vm-resource"
        get_current_template_mock.return_value = user_resource_template_without_enriching(user_resource_template_name, service_template_name)

        response = await client.get(app.url_path_for(strings.API_GET_USER_RESOURCE_TEMPLATE_BY_NAME, service_template_name=service_template_name, user_resource_template_name=user_resource_template_name))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == user_resource_template_name
        assert "description" in response.json()["required"]

    @pytest.mark.parametrize("exception, expected_status", [
        (EntityDoesNotExist, status.HTTP_404_NOT_FOUND),
        (DuplicateEntity, status.HTTP_500_INTERNAL_SERVER_ERROR),
        (UnableToAccessDatabase, status.HTTP_503_SERVICE_UNAVAILABLE)
    ])
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_template")
    async def test_get_user_resource_templates_by_name_returns_returns_error_status_based_on_exception(self, get_current_template_mock, exception, expected_status, app, client):
        service_template_name = "guacamole-service"
        user_resource_template_name = "vm-resource"
        get_current_template_mock.side_effect = exception

        response = await client.get(app.url_path_for(strings.API_GET_USER_RESOURCE_TEMPLATE_BY_NAME, service_template_name=service_template_name, user_resource_template_name=user_resource_template_name))

        assert response.status_code == expected_status
