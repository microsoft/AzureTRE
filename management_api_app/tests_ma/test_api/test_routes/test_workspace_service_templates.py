import json
import pytest
from mock import patch

from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import parse_obj_as
from starlette import status

from api.routes.workspaces import get_current_user
from db.errors import EntityDoesNotExist
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate
from models.domain.user_resource_template import UserResourceTemplate
from models.schemas.user_resource_template import UserResourceTemplateInCreate, UserResourceTemplateInResponse
from models.schemas.workspace_service_template import WorkspaceServiceTemplateInCreate
from models.schemas.workspace_template import WorkspaceTemplateInResponse, WorkspaceTemplateInCreate
from resources import strings
from services.concatjsonschema import enrich_workspace_service_schema_defs

pytestmark = pytest.mark.asyncio


class TestWorkspaceServiceTemplate:

    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, admin_user):
        app.dependency_overrides[get_current_user] = admin_user

    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
    async def test_when_updating_current_and_service_template_not_found_create_one(self, get_name_ver_mock,
                                                                                   get_current_mock,
                                                                                   create_item_mock,
                                                                                   app: FastAPI,
                                                                                   client: AsyncClient,
                                                                                   input_workspace_template: WorkspaceTemplateInCreate,
                                                                                   basic_workspace_service_template: ResourceTemplate):
        get_name_ver_mock.side_effect = EntityDoesNotExist
        get_current_mock.side_effect = EntityDoesNotExist

        create_item_mock.return_value = basic_workspace_service_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES),
                                     json=input_workspace_template.dict())
        assert response.status_code == status.HTTP_201_CREATED

    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.update_item")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
    async def test_when_updating_current_and_service_template_found_update_and_add(self,
                                                                                   get_resource_template_by_name_and_version,
                                                                                   get_current_workspace_template_by_name,
                                                                                   update_item_mock,
                                                                                   create_workspace_template_item,
                                                                                   app: FastAPI,
                                                                                   client: AsyncClient,
                                                                                   input_workspace_template: WorkspaceTemplateInCreate,
                                                                                   basic_workspace_service_template: ResourceTemplate):
        get_resource_template_by_name_and_version.side_effect = EntityDoesNotExist

        get_current_workspace_template_by_name.return_value = basic_workspace_service_template
        create_workspace_template_item.return_value = basic_workspace_service_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES),
                                     json=input_workspace_template.dict())

        updated_current_workspace_template = basic_workspace_service_template
        updated_current_workspace_template.current = False
        update_item_mock.assert_called_once_with(updated_current_workspace_template.dict())
        assert response.status_code == status.HTTP_201_CREATED

    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
    async def test_when_creating_service_template_enriched_service_template_is_returned(self,
                                                                                        get_resource_template_by_name_and_version,
                                                                                        get_current_workspace_template_by_name,
                                                                                        create_resource_template_item,
                                                                                        app: FastAPI,
                                                                                        client: AsyncClient,
                                                                                        input_workspace_template: WorkspaceServiceTemplateInCreate,
                                                                                        basic_workspace_service_template: ResourceTemplate):
        get_resource_template_by_name_and_version.side_effect = EntityDoesNotExist
        get_current_workspace_template_by_name.side_effect = EntityDoesNotExist

        create_resource_template_item.return_value = basic_workspace_service_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES),
                                     json=input_workspace_template.dict())

        expected_template = parse_obj_as(WorkspaceTemplateInResponse,
                                         enrich_workspace_service_schema_defs(basic_workspace_service_template))

        assert json.loads(response.text)["required"] == expected_template.required
        assert json.loads(response.text)["properties"] == expected_template.properties

    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_resource_template_by_name_and_version")
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

    @staticmethod
    def get_workspace_service_template_by_name_from_path_mock():
        return ResourceTemplate(
            id="1234-5678",
            name="my-tre-user-resource",
            description="These parameters are specific to my user resource template",
            version="0.0.1",
            resourceType=ResourceType.WorkspaceService,
            current=True,
            required=[],
            properties={}
        )

    @staticmethod
    def create_base_response_user_template(input_user_resource_template: UserResourceTemplateInCreate, parent_workspace_service_name):
        return UserResourceTemplate(
            id="1234-5678",
            name=input_user_resource_template.name,
            parentWorkspaceService=parent_workspace_service_name,
            description=input_user_resource_template.json_schema["description"],
            version=input_user_resource_template.version,
            resourceType=ResourceType.UserResource,
            current=True,
            required=input_user_resource_template.json_schema["required"],
            properties=input_user_resource_template.json_schema["properties"]
        )

    @patch("api.routes.workspace_service_templates.create_user_resource_template")
    @patch("api.dependencies.workspace_service_templates.UserResourceTemplateRepository.get_current_resource_template_by_name")
    async def test_when_creating_user_resource_template_template_returned_as_expected(self,
                                                                                      get_current_resource_mock,
                                                                                      create_user_resource_template_mock,
                                                                                      app: FastAPI, client: AsyncClient,
                                                                                      input_user_resource_template: UserResourceTemplateInCreate):
        # from api.routes.workspace_service_templates import get_workspace_service_template_by_name_from_path
        # app.dependency_overrides[get_workspace_service_template_by_name_from_path] = self.get_workspace_service_template_by_name_from_path_mock
        get_current_resource_mock.return_value = self.get_workspace_service_template_by_name_from_path_mock()

        parent_workspace_service_name = "guacamole"
        user_resource_template = self.create_base_response_user_template(input_user_resource_template, parent_workspace_service_name)
        create_user_resource_template_mock.return_value = user_resource_template

        expected_template = parse_obj_as(UserResourceTemplateInResponse, enrich_workspace_service_schema_defs(user_resource_template))

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE_TEMPLATES, template_name=parent_workspace_service_name),
                                     json=input_user_resource_template.dict())

        # reset the dependency overrides
        # app.dependency_overrides = {}

        assert response.json() == expected_template
