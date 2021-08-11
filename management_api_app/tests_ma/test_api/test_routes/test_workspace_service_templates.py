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
from models.schemas.resource_template import ResourceTemplateInformation
from models.schemas.workspace_service_template import WorkspaceServiceTemplateInCreate
from models.schemas.workspace_template import WorkspaceTemplateInResponse, WorkspaceTemplateInCreate
from resources import strings
from services.concatjsonschema import enrich_workspace_service_schema_defs

pytestmark = pytest.mark.asyncio


class TestWorkspaceServiceTemplates:

    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, admin_user):
        app.dependency_overrides[get_current_user] = admin_user

    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_basic_resource_templates_information")
    async def test_get_workspace_templates_returns_template_names_and_description(self, get_basic_resource_templates_info_mock, app: FastAPI, client: AsyncClient):
        expected_templates = [
            ResourceTemplateInformation(name="template1", description="description1"),
            ResourceTemplateInformation(name="template2", description="description2")
        ]
        get_basic_resource_templates_info_mock.return_value = expected_templates

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_TEMPLATES))

        assert response.status_code == status.HTTP_200_OK
        actual_templates = response.json()["templates"]
        assert len(actual_templates) == len(expected_templates)
        for template in expected_templates:
            assert template in actual_templates

    @patch("api.routes.workspace_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_workspace_template_by_name_and_version")
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

    @patch("api.routes.workspace_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.update_item")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_workspace_template_by_name_and_version")
    async def test_when_updating_current_and_service_template_found_update_and_add(self,
                                                                                   get_workspace_template_by_name_and_version,
                                                                                   get_current_workspace_template_by_name,
                                                                                   update_item_mock,
                                                                                   create_workspace_template_item,
                                                                                   app: FastAPI,
                                                                                   client: AsyncClient,
                                                                                   input_workspace_template: WorkspaceTemplateInCreate,
                                                                                   basic_workspace_service_template: ResourceTemplate):
        get_workspace_template_by_name_and_version.side_effect = EntityDoesNotExist

        get_current_workspace_template_by_name.return_value = basic_workspace_service_template
        create_workspace_template_item.return_value = basic_workspace_service_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES),
                                     json=input_workspace_template.dict())

        updated_current_workspace_template = basic_workspace_service_template
        updated_current_workspace_template.current = False
        update_item_mock.assert_called_once_with(updated_current_workspace_template.dict())
        assert response.status_code == status.HTTP_201_CREATED

    @patch("api.routes.workspace_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_workspace_template_by_name_and_version")
    async def test_when_creating_service_template_enriched_service_template_is_returned(self,
                                                                                        get_workspace_template_by_name_and_version,
                                                                                        get_current_workspace_template_by_name,
                                                                                        create_resource_template_item,
                                                                                        app: FastAPI,
                                                                                        client: AsyncClient,
                                                                                        input_workspace_template: WorkspaceServiceTemplateInCreate,
                                                                                        basic_workspace_service_template: ResourceTemplate):
        get_workspace_template_by_name_and_version.side_effect = EntityDoesNotExist
        get_current_workspace_template_by_name.side_effect = EntityDoesNotExist

        create_resource_template_item.return_value = basic_workspace_service_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES),
                                     json=input_workspace_template.dict())

        expected_template = parse_obj_as(WorkspaceTemplateInResponse,
                                         enrich_workspace_service_schema_defs(basic_workspace_service_template))

        assert json.loads(response.text)["required"] == expected_template.required
        assert json.loads(response.text)["properties"] == expected_template.properties

    @patch("api.routes.workspace_templates.ResourceTemplateRepository.create_resource_template_item")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_current_resource_template_by_name")
    @patch("api.routes.workspace_templates.ResourceTemplateRepository.get_workspace_template_by_name_and_version")
    async def test_when_creating_workspace_service_template_service_resource_type_is_set(self,
                                                                                         get_workspace_template_by_name_and_version,
                                                                                         get_current_workspace_template_by_name,
                                                                                         create_workspace_template_item_mock,
                                                                                         app: FastAPI,
                                                                                         client: AsyncClient,
                                                                                         input_workspace_template: WorkspaceTemplateInCreate,
                                                                                         basic_workspace_service_template: ResourceTemplate):
        get_workspace_template_by_name_and_version.side_effect = EntityDoesNotExist
        get_current_workspace_template_by_name.side_effect = EntityDoesNotExist

        create_workspace_template_item_mock.return_value = basic_workspace_service_template

        await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES),
                          json=input_workspace_template.dict())

        create_workspace_template_item_mock.assert_called_once_with(input_workspace_template,
                                                                    ResourceType.WorkspaceService)
