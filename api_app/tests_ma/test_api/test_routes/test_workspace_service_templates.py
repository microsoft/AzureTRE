import json
import pytest
from mock import patch

from pydantic import parse_obj_as
from starlette import status

from services.authentication import get_current_admin_user, get_current_tre_user_or_tre_admin
from db.errors import EntityDoesNotExist, EntityVersionExist, InvalidInput, UnableToAccessDatabase
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate
from models.schemas.resource_template import ResourceTemplateInformation
from models.domain.user_resource_template import UserResourceTemplate
from models.schemas.workspace_template import WorkspaceTemplateInResponse
from resources import strings
from services.schema_service import enrich_workspace_service_template

pytestmark = pytest.mark.asyncio


@pytest.fixture
def workspace_service_template_without_enriching():
    def create_workspace_service_template(template_name: str = "base-service-template"):
        return ResourceTemplate(
            id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
            name=template_name,
            description="base service bundle",
            version="0.1.0",
            resourceType=ResourceType.WorkspaceService,
            current=True,
            type="object",
            required=[],
            properties={},
            actions=[]
        )
    return create_workspace_service_template


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
            customActions=[],
            parentWorkspaceService=parent_service
        )
    return create_user_resource_template


class TestWorkspaceServiceTemplatesRequiringAdminRights:
    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, admin_user):
        app.dependency_overrides[get_current_tre_user_or_tre_admin] = admin_user
        app.dependency_overrides[get_current_admin_user] = admin_user
        yield
        app.dependency_overrides = {}

    # GET /workspace-service-templates/
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_templates_information")
    async def test_get_workspace_service_templates_returns_template_names_and_description(self, get_templates_info_mock, app, client):
        expected_template_infos = [
            ResourceTemplateInformation(name="template1", title="template 1", description="description1"),
            ResourceTemplateInformation(name="template2", title="template 2", description="description2")
        ]
        get_templates_info_mock.return_value = expected_template_infos

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_TEMPLATES))

        assert response.status_code == status.HTTP_200_OK
        actual_template_infos = response.json()["templates"]
        assert len(actual_template_infos) == len(expected_template_infos)
        for template_info in expected_template_infos:
            assert template_info in actual_template_infos

    # GET /workspace-service-templates-enabled-versions/
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_templates_enabled_versions")
    async def test_get_workspace_service_templates_enabled_versions_returns_versions(self, get_templates_version_info_mock, app, client):
        expected_template_version_infos = [
            {
                "name": "tre-service-guacamole",
                "title": "Apache Guacamole - Virtual Desktop Service",
                "versions": [
                    {
                        "version": "0.12.6",
                        "description": "Enables Windows and Linux virtual machines to be accessed via Apache Guacamole.",
                        "enabled": {"TRE": False, "Workspace": True},
                    }
                ],
                "user-resources": [
                    {
                        "name": "tre-service-guacamole-linuxvm",
                        "versions": [
                            {
                                "version": "1.2.3",
                                "description": "Linux virtual machine.",
                                "enabled": {"TRE": False, "Workspace": True},
                            }
                        ],
                    },
                    {
                        "name": "tre-service-guacamole-windowsvm",
                        "versions": [
                            {
                                "version": "1.2.3",
                                "description": "Windows virtual machine.",
                                "enabled": {"TRE": False, "Workspace": True},
                            }
                        ],
                    },
                ],
            },
            {
                "name": "tre-service-databricks",
                "title": "Azure Databricks",
                "versions": [
                    {
                        "version": "1.0.10",
                        "description": "Azure Databricks",
                        "enabled": {"TRE": False, "Workspace": True},
                    }
                ],
            },
            {
                "name": "tre-service-azureml",
                "title": "Azure Machine Learning",
                "versions": [
                    {
                        "version": "0.9.2",
                        "description": "Azure Machine Learning",
                        "enabled": {"TRE": False, "Workspace": True},
                    }
                ],
                "user-resources": [
                    {
                        "name": "tre-user-resource-aml-compute-instance",
                        "versions": [
                            {
                                "version": "0.5.11",
                                "description": "An Azure Machine Learning compute instance is a managed cloud-based workstation for data scientists. Each compute instance has only one owner, although you can share files between multiple compute instances.",
                                "enabled": {"TRE": False, "Workspace": True},
                            }
                        ]
                    }
                ]
            }
        ]

        get_templates_version_info_mock.return_value = expected_template_version_infos

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_TEMPLATES_ENABLED_VERSIONS))

        assert response.status_code == status.HTTP_200_OK
        actual_template_version_infos = response.json()["service_template_versions"]
        assert len(actual_template_version_infos) == len(expected_template_version_infos)
        for template_version_info in expected_template_version_infos:
            assert template_version_info in actual_template_version_infos


    # POST /workspace-service-templates/
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_template")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_template")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_template_by_name_and_version")
    async def test_when_updating_current_and_service_template_not_found_create_one(self, get_name_ver_mock, get_current_mock, create_template_mock, app, client, input_workspace_template, basic_workspace_service_template):
        get_name_ver_mock.side_effect = EntityDoesNotExist
        get_current_mock.side_effect = EntityDoesNotExist
        create_template_mock.return_value = basic_workspace_service_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES), json=input_workspace_template.dict())

        assert response.status_code == status.HTTP_201_CREATED

    # POST /workspace-service-templates/
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_template")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.update_item")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_template")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_template_by_name_and_version")
    async def test_when_updating_current_and_service_template_found_update_and_add(self, get_template_by_name_and_version_mock, get_current_template_mock, update_item_mock, create_template_mock, app, client, input_workspace_template, basic_workspace_service_template):
        get_template_by_name_and_version_mock.side_effect = EntityDoesNotExist

        get_current_template_mock.return_value = basic_workspace_service_template
        create_template_mock.return_value = basic_workspace_service_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES), json=input_workspace_template.dict())

        updated_current_workspace_template = basic_workspace_service_template
        updated_current_workspace_template.current = False
        update_item_mock.assert_called_once_with(updated_current_workspace_template.dict())
        assert response.status_code == status.HTTP_201_CREATED

    # POST /workspace-service-templates/
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_template")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_template")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_template_by_name_and_version")
    async def test_when_creating_service_template_enriched_service_template_is_returned(self, get_template_by_name_and_version_mock, get_current_template_mock, create_template_mock, app, client, input_workspace_template, basic_workspace_service_template):
        get_template_by_name_and_version_mock.side_effect = EntityDoesNotExist
        get_current_template_mock.side_effect = EntityDoesNotExist
        create_template_mock.return_value = basic_workspace_service_template

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES), json=input_workspace_template.dict())

        expected_template = parse_obj_as(WorkspaceTemplateInResponse, enrich_workspace_service_template(basic_workspace_service_template))
        assert json.loads(response.text)["required"] == expected_template.dict(exclude_unset=True)["required"]
        assert json.loads(response.text)["properties"] == expected_template.dict(exclude_unset=True)["properties"]

    # POST /workspace-service-templates/
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_template")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_template")
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_template_by_name_and_version")
    async def test_when_creating_workspace_service_template_service_resource_type_is_set(self, get_template_by_name_and_version_mock, get_current_template_mock, create_template_mock, app, client, input_workspace_service_template, basic_workspace_service_template):
        get_template_by_name_and_version_mock.side_effect = EntityDoesNotExist
        get_current_template_mock.side_effect = EntityDoesNotExist
        create_template_mock.return_value = basic_workspace_service_template

        await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES), json=input_workspace_service_template.dict())

        create_template_mock.assert_called_once_with(input_workspace_service_template, ResourceType.WorkspaceService, '')

    # POST /workspace-service-templates/
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_and_validate_template", side_effect=EntityVersionExist)
    async def test_creating_a_template_raises_409_conflict_if_template_version_exists(self, _, client, app, input_workspace_service_template):
        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES), json=input_workspace_service_template.dict())

        assert response.status_code == status.HTTP_409_CONFLICT

    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_and_validate_template", side_effect=InvalidInput)
    async def test_creating_a_workspace_service_template_raises_http_422_if_step_ids_are_duplicated(self, _, client, app, input_workspace_service_template):
        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES), json=input_workspace_service_template.dict())

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # GET /workspace-service-templates/{template_name}
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_template")
    async def test_workspace_service_templates_by_name_returns_enriched_workspace_service_template(self, get_current_template_mock, workspace_service_template_without_enriching, app, client):
        template_name = "template1"
        get_current_template_mock.return_value = workspace_service_template_without_enriching(template_name)

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_TEMPLATE_BY_NAME, service_template_name=template_name))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == template_name
        assert "description" in response.json()["required"]

    # GET /workspace-service-templates/{template_name}
    @pytest.mark.parametrize("exception, expected_status", [
        (EntityDoesNotExist, status.HTTP_404_NOT_FOUND),
        (UnableToAccessDatabase, status.HTTP_503_SERVICE_UNAVAILABLE)
    ])
    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.get_current_template")
    async def test_workspace_service_templates_by_name_returns_error_status_based_on_exception(self, get_current_template_mock, exception, expected_status, app, client):
        get_current_template_mock.side_effect = exception

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_TEMPLATE_BY_NAME, service_template_name="template1"))

        assert response.status_code == expected_status
