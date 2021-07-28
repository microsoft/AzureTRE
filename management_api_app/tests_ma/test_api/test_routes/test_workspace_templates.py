import json
import pytest
from mock import patch

from fastapi import FastAPI
from starlette import status
from httpx import AsyncClient

from resources import strings
from api.routes.workspaces import get_current_user
from db.errors import EntityDoesNotExist, UnableToAccessDatabase
from models.domain.resource_template import ResourceTemplate, ResourceType
from models.schemas.workspace_template import WorkspaceTemplateInResponse, get_sample_workspace_template_object, WorkspaceTemplateInCreate

from services.concatjsonschema import enrich_schema_defs
from pydantic import parse_obj_as

pytestmark = pytest.mark.asyncio


class TestWorkspaceTemplate:

    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, admin_user):
        app.dependency_overrides[get_current_user] = admin_user

    @staticmethod
    @pytest.fixture
    def input_workspace_template():
        return WorkspaceTemplateInCreate(
            name="my-tre-workspace",
            version="0.0.1",
            current=True,
            json_schema={
                "$schema": "http://json-schema.org/draft-07/schema",
                "$id": "https://github.com/microsoft/AzureTRE/templates/workspaces/myworkspace/workspace.json",
                "type": "object",
                "title": "My Workspace Template Custom Parameters",
                "description": "These parameters are specific to my workspace template",
                "required": [],
                "properties": {}
            })

    @staticmethod
    @pytest.fixture
    def basic_resource_template(input_workspace_template):
        return ResourceTemplate(
            id="1234-5678",
            name=input_workspace_template.name,
            description=input_workspace_template.json_schema["description"],
            version=input_workspace_template.name,
            resourceType=ResourceType.Workspace,
            current=True,
            required=input_workspace_template.json_schema["required"],
            properties=input_workspace_template.json_schema["properties"]
        )

    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_workspace_template_names")
    async def test_workspace_templates_returns_template_names(self, get_workspace_template_names_mock, app: FastAPI, client: AsyncClient):
        expected_template_names = ["template1", "template2"]
        get_workspace_template_names_mock.return_value = expected_template_names

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_TEMPLATES))

        assert response.status_code == status.HTTP_200_OK

        actual_template_names = response.json()["templateNames"]
        assert len(actual_template_names) == len(expected_template_names)
        for name in expected_template_names:
            assert name in actual_template_names

    async def test_post_does_not_create_a_template_with_bad_payload(self, app: FastAPI, client: AsyncClient):
        input_data = """
                        {
                            "blah": "blah"
                        }
        """

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES), json=input_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.create_workspace_template_item")
    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_current_workspace_template_by_name")
    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_workspace_template_by_name_and_version")
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

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES), json=input_workspace_template.dict())
        assert response.status_code == status.HTTP_201_CREATED

    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.create_workspace_template_item")
    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.update_item")
    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_current_workspace_template_by_name")
    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_workspace_template_by_name_and_version")
    async def test_when_updating_current_and_template_found_update_and_add(self, get_workspace_template_by_name_and_version,
                                                                           get_current_workspace_template_by_name,
                                                                           update_item_mock,
                                                                           create_workspace_template_item,
                                                                           app: FastAPI,
                                                                           client: AsyncClient,
                                                                           input_workspace_template: WorkspaceTemplateInCreate,
                                                                           basic_resource_template: ResourceTemplate):
        get_workspace_template_by_name_and_version.side_effect = EntityDoesNotExist

        get_current_workspace_template_by_name.return_value = basic_resource_template
        create_workspace_template_item.return_value = basic_resource_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES), json=input_workspace_template.dict())

        updated_current_workspace_template = basic_resource_template
        updated_current_workspace_template.current = False
        update_item_mock.assert_called_once_with(updated_current_workspace_template.dict())
        assert response.status_code == status.HTTP_201_CREATED

    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_workspace_template_by_name_and_version")
    async def test_same_name_and_version_template_not_allowed(self, mock, app: FastAPI, client: AsyncClient, input_workspace_template: WorkspaceTemplateInCreate):
        mock.return_value = ["exists"]

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES), json=input_workspace_template.dict())

        assert response.status_code == status.HTTP_409_CONFLICT

    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_current_workspace_template_by_name")
    async def test_workspace_templates_by_name_returns_workspace_template(self, get_workspace_template_by_name_mock, app: FastAPI, client: AsyncClient):
        get_workspace_template_by_name_mock.return_value = get_sample_workspace_template_object(template_name="template1")

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_TEMPLATE_BY_NAME, template_name="tre-workspace-vanilla"))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "template1"

    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_current_workspace_template_by_name")
    async def test_workspace_templates_by_name_returns_404_if_template_does_not_exist(self, get_workspace_template_by_name_mock, app: FastAPI, client: AsyncClient):
        get_workspace_template_by_name_mock.side_effect = EntityDoesNotExist

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_TEMPLATE_BY_NAME, template_name="tre-workspace-vanilla"))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_current_workspace_template_by_name")
    async def test_workspace_templates_by_name_returns_503_on_database_error(self, get_workspace_template_by_name_mock, app: FastAPI, client: AsyncClient):
        get_workspace_template_by_name_mock.side_effect = UnableToAccessDatabase

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_TEMPLATE_BY_NAME, template_name="tre-workspace-vanilla"))

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.create_workspace_template_item")
    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_current_workspace_template_by_name")
    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_workspace_template_by_name_and_version")
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

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES), json=input_workspace_template.dict())

        assert response.status_code == status.HTTP_201_CREATED
        assert json.loads(response.text)["current"]

    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.create_workspace_template_item")
    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_current_workspace_template_by_name")
    @ patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_workspace_template_by_name_and_version")
    async def test_when_creating_template_enriched_template_is_returned(self, get_workspace_template_by_name_and_version,
                                                                        get_current_workspace_template_by_name,
                                                                        create_workspace_template_item,
                                                                        app: FastAPI,
                                                                        client: AsyncClient,
                                                                        input_workspace_template: WorkspaceTemplateInCreate,
                                                                        basic_resource_template: ResourceTemplate):
        get_workspace_template_by_name_and_version.side_effect = EntityDoesNotExist
        get_current_workspace_template_by_name.side_effect = EntityDoesNotExist

        create_workspace_template_item.return_value = basic_resource_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES), json=input_workspace_template.dict())

        expected_template = parse_obj_as(WorkspaceTemplateInResponse, enrich_schema_defs(basic_resource_template))

        assert json.loads(response.text)["required"] == expected_template.required
        assert json.loads(response.text)["properties"] == expected_template.properties
