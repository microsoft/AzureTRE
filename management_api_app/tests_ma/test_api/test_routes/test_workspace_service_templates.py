import json
import pytest
from mock import patch

from pydantic import parse_obj_as
from starlette import status

from api.routes.workspaces import get_current_user
from db.errors import EntityDoesNotExist, EntityVersionExist, UnableToAccessDatabase
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate
from models.schemas.resource_template import ResourceTemplateInformation
from models.schemas.user_resource_template import UserResourceTemplateInResponse
from models.schemas.workspace_template import WorkspaceTemplateInResponse
from resources import strings
from services.concatjsonschema import enrich_workspace_service_schema_defs

pytestmark = pytest.mark.asyncio


@pytest.fixture
def workspace_service_template_without_enriching():
    def create_workspace_service_template(template_name: str = "vanilla-service-template"):
        return ResourceTemplate(
            id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
            name=template_name,
            description="vanilla service bundle",
            version="0.1.0",
            resourceType=ResourceType.WorkspaceService,
            current=True,
            type="object",
            required=[],
            properties={}
        )
    return create_workspace_service_template


class TestWorkspaceServiceTemplatesRequiringAdminRights:
    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, admin_user):
        app.dependency_overrides[get_current_user] = admin_user
        yield
        app.dependency_overrides = {}

    # GET /workspace-service-templates/
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_templates_information")
    async def test_get_workspace_service_templates_returns_template_names_and_description(self, get_templates_info_mock, app, client):
        expected_template_infos = [
            ResourceTemplateInformation(name="template1", description="description1"),
            ResourceTemplateInformation(name="template2", description="description2")
        ]
        get_templates_info_mock.return_value = expected_template_infos

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_TEMPLATES))

        assert response.status_code == status.HTTP_200_OK
        actual_template_infos = response.json()["templates"]
        assert len(actual_template_infos) == len(expected_template_infos)
        for template_info in expected_template_infos:
            assert template_info in actual_template_infos

    # POST /workspace-service-templates/
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
    async def test_when_updating_current_and_service_template_not_found_create_one(self, get_name_ver_mock, get_current_mock, create_item_mock, app, client, input_workspace_template, basic_workspace_service_template):
        get_name_ver_mock.side_effect = EntityDoesNotExist
        get_current_mock.side_effect = EntityDoesNotExist

        create_item_mock.return_value = basic_workspace_service_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES), json=input_workspace_template.dict())
        assert response.status_code == status.HTTP_201_CREATED

    # POST /workspace-service-templates/
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.update_item")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
    async def test_when_updating_current_and_service_template_found_update_and_add(self, get_resource_template_by_name_and_version, get_current_workspace_template_by_name, update_item_mock, create_workspace_template_item_mock, app, client, input_workspace_template, basic_workspace_service_template):
        get_resource_template_by_name_and_version.side_effect = EntityDoesNotExist

        get_current_workspace_template_by_name.return_value = basic_workspace_service_template
        create_workspace_template_item_mock.return_value = basic_workspace_service_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES), json=input_workspace_template.dict())

        updated_current_workspace_template = basic_workspace_service_template
        updated_current_workspace_template.current = False
        update_item_mock.assert_called_once_with(updated_current_workspace_template.dict())
        assert response.status_code == status.HTTP_201_CREATED

    # POST /workspace-service-templates/
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
    async def test_when_creating_service_template_enriched_service_template_is_returned(self, get_resource_template_by_name_and_version, get_current_workspace_template_by_name, create_resource_template_item, app, client, input_workspace_template, basic_workspace_service_template):
        get_resource_template_by_name_and_version.side_effect = EntityDoesNotExist
        get_current_workspace_template_by_name.side_effect = EntityDoesNotExist

        create_resource_template_item.return_value = basic_workspace_service_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES), json=input_workspace_template.dict())

        expected_template = parse_obj_as(WorkspaceTemplateInResponse, enrich_workspace_service_schema_defs(basic_workspace_service_template))

        assert json.loads(response.text)["required"] == expected_template.required
        assert json.loads(response.text)["properties"] == expected_template.properties

    # POST /workspace-service-templates/
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
    async def test_when_creating_workspace_service_template_service_resource_type_is_set(self, get_resource_template_by_name_and_version, get_current_workspace_template_by_name, create_workspace_template_item_mock, app, client, input_workspace_template, basic_workspace_service_template):
        get_resource_template_by_name_and_version.side_effect = EntityDoesNotExist
        get_current_workspace_template_by_name.side_effect = EntityDoesNotExist

        create_workspace_template_item_mock.return_value = basic_workspace_service_template

        await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES), json=input_workspace_template.dict())

        create_workspace_template_item_mock.assert_called_once_with(input_workspace_template, ResourceType.WorkspaceService)

    # GET /workspace-service-templates/{template_name}
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    async def test_workspace_service_templates_by_name_returns_enriched_workspace_service_template(self, get_workspace_service_template_by_name_mock, workspace_service_template_without_enriching, app, client):
        template_name = "template1"
        get_workspace_service_template_by_name_mock.return_value = workspace_service_template_without_enriching(template_name)

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_TEMPLATE_BY_NAME, template_name=template_name))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == template_name
        assert "description" in response.json()["required"]

    # GET /workspace-service-templates/{template_name}
    @pytest.mark.parametrize("exception, expected_status", [
        (EntityDoesNotExist, status.HTTP_404_NOT_FOUND),
        (UnableToAccessDatabase, status.HTTP_503_SERVICE_UNAVAILABLE)
    ])
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    async def test_workspace_service_templates_by_name_returns_error_status_based_on_exception(self, get_workspace_service_template_by_name_mock, exception, expected_status, app, client):
        get_workspace_service_template_by_name_mock.side_effect = exception

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_TEMPLATE_BY_NAME, template_name="template1"))

        assert response.status_code == expected_status

    # POST /workspace-service-templates/{template_name}/user-resource-templates
    @patch("api.routes.workspace_service_templates.create_user_resource_template")
    @patch("api.dependencies.workspace_service_templates.UserResourceTemplateRepository.get_current_resource_template_by_name")
    async def test_when_creating_user_resource_template_it_is_returned_as_expected(self, get_current_resource_mock, create_user_resource_template_mock, app, client, input_user_resource_template, basic_workspace_service_template, basic_user_resource_template):
        get_current_resource_mock.return_value = basic_workspace_service_template

        parent_workspace_service_name = "guacamole"
        basic_user_resource_template.parentWorkspaceService = parent_workspace_service_name
        create_user_resource_template_mock.return_value = basic_user_resource_template

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE_TEMPLATES, template_name=parent_workspace_service_name), json=input_user_resource_template.dict())

        assert json.loads(response.text)["resourceType"] == ResourceType.UserResource
        assert json.loads(response.text)["parentWorkspaceService"] == parent_workspace_service_name
        assert json.loads(response.text)["name"] == basic_user_resource_template.name

    # POST /workspace-service-templates/{template_name}/user-resource-templates
    @patch("api.routes.workspace_service_templates.create_user_resource_template")
    @patch("api.dependencies.workspace_service_templates.UserResourceTemplateRepository.get_current_resource_template_by_name")
    async def test_when_creating_user_resource_template_enriched_service_template_is_returned(self, get_current_resource_mock, create_user_resource_template_mock, app, client, input_user_resource_template, basic_workspace_service_template, basic_user_resource_template):
        get_current_resource_mock.return_value = basic_workspace_service_template

        parent_workspace_service_name = "guacamole"
        basic_user_resource_template.parentWorkspaceService = parent_workspace_service_name
        create_user_resource_template_mock.return_value = basic_user_resource_template

        expected_template = parse_obj_as(UserResourceTemplateInResponse, enrich_workspace_service_schema_defs(basic_user_resource_template))

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE_TEMPLATES, template_name=parent_workspace_service_name), json=input_user_resource_template.dict())

        assert json.loads(response.text)["properties"] == expected_template.properties
        assert json.loads(response.text)["required"] == expected_template.required

    # POST /workspace-service-templates/{template_name}/user-resource-templates
    @patch("api.routes.workspace_service_templates.create_user_resource_template")
    @patch("api.dependencies.workspace_service_templates.UserResourceTemplateRepository.get_current_resource_template_by_name")
    async def test_when_creating_user_resource_template_returns_409_if_version_exists(self, get_current_resource_mock, create_user_resource_template_mock, app, client, input_user_resource_template, basic_workspace_service_template, basic_user_resource_template):
        get_current_resource_mock.return_value = basic_workspace_service_template

        parent_workspace_service_name = "guacamole"
        basic_user_resource_template.parentWorkspaceService = parent_workspace_service_name
        create_user_resource_template_mock.side_effect = EntityVersionExist

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE_TEMPLATES, template_name=parent_workspace_service_name), json=input_user_resource_template.dict())

        assert response.status_code == status.HTTP_409_CONFLICT


class TestWorkspaceServiceTemplatesNotRequiringAdminRights:
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_basic_template_infos_for_user_resource_templates_matching_service_template")
    async def test_get_workspace_templates_returns_template_names_and_description(self, get_basic_resource_templates_info_mock, app, client):
        expected_templates = [
            ResourceTemplateInformation(name="template1", description="description1"),
            ResourceTemplateInformation(name="template2", description="description2")
        ]
        get_basic_resource_templates_info_mock.return_value = expected_templates

        response = await client.get(app.url_path_for(strings.API_GET_USER_RESOURCE_TEMPLATES, template_name="parent_service_name"))

        assert response.status_code == status.HTTP_200_OK
        actual_templates = response.json()["templates"]
        assert len(actual_templates) == len(expected_templates)
        for template in expected_templates:
            assert template in actual_templates
