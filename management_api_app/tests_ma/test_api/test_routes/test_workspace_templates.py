import json
import pytest
from mock import patch

from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import parse_obj_as
from starlette import status

from models.domain.resource import ResourceType
from resources import strings
from api.routes.workspaces import get_current_user
from db.errors import EntityDoesNotExist, UnableToAccessDatabase
from models.domain.resource_template import ResourceTemplate
from models.schemas.workspace_template import WorkspaceTemplateInResponse, WorkspaceTemplateInCreate
from services.concatjsonschema import enrich_workspace_schema_defs


pytestmark = pytest.mark.asyncio


@pytest.fixture
def workspace_template_without_enriching():
    def create_workspace_template(template_name: str = "vanilla-workspace-template"):
        return ResourceTemplate(
            id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
            name=template_name,
            description="vanilla workspace bundle",
            version="0.1.0",
            resourceType=ResourceType.Workspace,
            current=True,
            type="object",
            required=[],
            properties={}
        )
    return create_workspace_template


class TestWorkspaceTemplate:

    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, admin_user):
        app.dependency_overrides[get_current_user] = admin_user
        yield
        app.dependency_overrides = {}

    # GET /workspace-templates
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_workspace_template_names")
    async def test_workspace_templates_returns_template_names(self, get_workspace_template_names_mock, app: FastAPI,
                                                              client: AsyncClient):
        expected_template_names = ["template1", "template2"]
        get_workspace_template_names_mock.return_value = expected_template_names

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_TEMPLATES))

        assert response.status_code == status.HTTP_200_OK

        actual_template_names = response.json()["templateNames"]
        assert len(actual_template_names) == len(expected_template_names)
        for name in expected_template_names:
            assert name in actual_template_names

    # POST /workspace-templates
    async def test_post_does_not_create_a_template_with_bad_payload(self, app: FastAPI, client: AsyncClient):
        input_data = """
                        {
                            "blah": "blah"
                        }
        """

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES), json=input_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # POST /workspace-templates
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
    async def test_when_updating_current_and_template_not_found_create_one(self, get_name_ver_mock,
                                                                           get_current_mock,
                                                                           create_item_mock,
                                                                           app: FastAPI,
                                                                           client: AsyncClient,
                                                                           input_workspace_template: WorkspaceTemplateInCreate,
                                                                           basic_resource_template: ResourceTemplate):
        get_name_ver_mock.side_effect = EntityDoesNotExist
        get_current_mock.side_effect = EntityDoesNotExist

        create_item_mock.return_value = basic_resource_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES),
                                     json=input_workspace_template.dict())
        assert response.status_code == status.HTTP_201_CREATED

    # POST /workspace-templates
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.update_item")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
    async def test_when_updating_current_and_template_found_update_and_add(self,
                                                                           get_resource_template_by_name_and_version,
                                                                           get_current_workspace_template_by_name,
                                                                           update_item_mock,
                                                                           create_workspace_template_item,
                                                                           app: FastAPI,
                                                                           client: AsyncClient,
                                                                           input_workspace_template: WorkspaceTemplateInCreate,
                                                                           basic_resource_template: ResourceTemplate):
        get_resource_template_by_name_and_version.side_effect = EntityDoesNotExist

        get_current_workspace_template_by_name.return_value = basic_resource_template
        create_workspace_template_item.return_value = basic_resource_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES),
                                     json=input_workspace_template.dict())

        updated_current_workspace_template = basic_resource_template
        updated_current_workspace_template.current = False
        update_item_mock.assert_called_once_with(updated_current_workspace_template.dict())
        assert response.status_code == status.HTTP_201_CREATED

    # POST /workspace-templates
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
    async def test_same_name_and_version_template_not_allowed(self, mock, app: FastAPI, client: AsyncClient,
                                                              input_workspace_template: WorkspaceTemplateInCreate):
        mock.return_value = ["exists"]

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES),
                                     json=input_workspace_template.dict())

        assert response.status_code == status.HTTP_409_CONFLICT

    # GET /workspace-templates/{template_name}
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    async def test_workspace_templates_by_name_returns_enriched_workspace_template(self, get_workspace_template_by_name_mock,
                                                                                   app: FastAPI, client: AsyncClient, workspace_template_without_enriching):
        template_name = "template1"
        get_workspace_template_by_name_mock.return_value = workspace_template_without_enriching(template_name)

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_TEMPLATE_BY_NAME, template_name=template_name))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == template_name
        assert "description" in response.json()["required"]

    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    async def test_workspace_templates_by_name_returns_404_if_template_does_not_exist(self,
                                                                                      get_workspace_template_by_name_mock,
                                                                                      app: FastAPI,
                                                                                      client: AsyncClient):
        get_workspace_template_by_name_mock.side_effect = EntityDoesNotExist

        response = await client.get(
            app.url_path_for(strings.API_GET_WORKSPACE_TEMPLATE_BY_NAME, template_name="tre-workspace-vanilla"))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    async def test_workspace_templates_by_name_returns_503_on_database_error(self, get_workspace_template_by_name_mock,
                                                                             app: FastAPI, client: AsyncClient):
        get_workspace_template_by_name_mock.side_effect = UnableToAccessDatabase

        response = await client.get(
            app.url_path_for(strings.API_GET_WORKSPACE_TEMPLATE_BY_NAME, template_name="tre-workspace-vanilla"))

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.workspace_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
    async def test_when_not_updating_current_and_new_registration_current_is_enforced(self, get_name_ver_mock,
                                                                                      get_current_mock,
                                                                                      create_item_mock,
                                                                                      app: FastAPI,
                                                                                      client: AsyncClient,
                                                                                      input_workspace_template: WorkspaceTemplateInCreate,
                                                                                      basic_resource_template: ResourceTemplate):
        input_workspace_template.current = False
        get_name_ver_mock.side_effect = EntityDoesNotExist
        get_current_mock.side_effect = EntityDoesNotExist

        create_item_mock.return_value = basic_resource_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES),
                                     json=input_workspace_template.dict())

        assert response.status_code == status.HTTP_201_CREATED
        assert json.loads(response.text)["current"]

    @patch("api.routes.workspace_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
    async def test_when_creating_template_enriched_template_is_returned(self,
                                                                        get_resource_template_by_name_and_version,
                                                                        get_current_workspace_template_by_name,
                                                                        create_resource_template_item,
                                                                        app: FastAPI,
                                                                        client: AsyncClient,
                                                                        input_workspace_template: WorkspaceTemplateInCreate,
                                                                        basic_resource_template: ResourceTemplate):
        get_resource_template_by_name_and_version.side_effect = EntityDoesNotExist
        get_current_workspace_template_by_name.side_effect = EntityDoesNotExist

        create_resource_template_item.return_value = basic_resource_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES),
                                     json=input_workspace_template.dict())

        expected_template = parse_obj_as(WorkspaceTemplateInResponse, enrich_workspace_schema_defs(basic_resource_template))

        assert json.loads(response.text)["required"] == expected_template.required
        assert json.loads(response.text)["properties"] == expected_template.properties

    @patch("api.routes.workspace_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
    async def test_when_creating_workspace_template_workspace_resource_type_is_set(self,
                                                                                   get_resource_template_by_name_and_version,
                                                                                   get_current_workspace_template_by_name,
                                                                                   create_workspace_template_item_mock,
                                                                                   app: FastAPI,
                                                                                   client: AsyncClient,
                                                                                   input_workspace_template: WorkspaceTemplateInCreate,
                                                                                   basic_resource_template: ResourceTemplate):
        get_resource_template_by_name_and_version.side_effect = EntityDoesNotExist
        get_current_workspace_template_by_name.side_effect = EntityDoesNotExist

        create_workspace_template_item_mock.return_value = basic_resource_template

        await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES),
                          json=input_workspace_template.dict())

        create_workspace_template_item_mock.assert_called_once_with(input_workspace_template, ResourceType.Workspace)

    @patch("api.routes.workspace_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
    async def test_when_creating_workspace_service_template_service_resource_type_is_set(self,
                                                                                         get_resource_template_by_name_and_version,
                                                                                         get_current_workspace_template_by_name,
                                                                                         create_workspace_template_item_mock,
                                                                                         app: FastAPI,
                                                                                         client: AsyncClient,
                                                                                         input_workspace_template: WorkspaceTemplateInCreate,
                                                                                         basic_workspace_service_template: ResourceTemplate):
        get_resource_template_by_name_and_version.side_effect = EntityDoesNotExist
        get_current_workspace_template_by_name.side_effect = EntityDoesNotExist

        create_workspace_template_item_mock.return_value = basic_workspace_service_template

        await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES),
                          json=input_workspace_template.dict())

        create_workspace_template_item_mock.assert_called_once_with(input_workspace_template,
                                                                    ResourceType.WorkspaceService)
