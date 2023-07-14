import json
import pytest
from mock import patch

from pydantic import parse_obj_as
from starlette import status

from db.errors import EntityDoesNotExist, EntityVersionExist, InvalidInput, UnableToAccessDatabase
from services.authentication import get_current_admin_user, get_current_tre_user_or_tre_admin
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate
from models.schemas.resource_template import ResourceTemplateInformation
from models.schemas.shared_service_template import SharedServiceTemplateInResponse
from resources import strings
from services.schema_service import enrich_shared_service_template

pytestmark = pytest.mark.asyncio


@pytest.fixture
def shared_service_template():
    def create_shared_service_template(template_name: str = "base-shared-service-template"):
        return ResourceTemplate(
            id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
            name=template_name,
            description="base shared service",
            version="0.1.0",
            resourceType=ResourceType.SharedService,
            current=True,
            type="object",
            required=[],
            properties={},
            actions=[]
        )
    return create_shared_service_template


class TestSharedServiceTemplates:
    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, admin_user):
        app.dependency_overrides[get_current_tre_user_or_tre_admin] = admin_user
        app.dependency_overrides[get_current_admin_user] = admin_user
        yield
        app.dependency_overrides = {}

    # GET /shared-service-templates/
    @patch("api.routes.shared_service_templates.ResourceTemplateRepository.get_templates_information")
    async def test_get_shared_service_templates_returns_template_names_and_description(self, get_templates_info_mock, app, client):
        expected_template_infos = [
            ResourceTemplateInformation(name="template1", title="template 1", description="description1"),
            ResourceTemplateInformation(name="template2", title="template 2", description="description2")
        ]
        get_templates_info_mock.return_value = expected_template_infos

        response = await client.get(app.url_path_for(strings.API_GET_SHARED_SERVICE_TEMPLATES))

        assert response.status_code == status.HTTP_200_OK
        actual_template_infos = response.json()["templates"]
        assert len(actual_template_infos) == len(expected_template_infos)
        for template_info in expected_template_infos:
            assert template_info in actual_template_infos

    # GET /shared-service-templates/{service_template_name}
    @patch("api.routes.shared_service_templates.ResourceTemplateRepository.get_current_template")
    async def test_get_shared_service_template_by_name_returns_enriched_template(self, get_current_template_mock, app, client, shared_service_template):
        template_name = "template1"
        get_current_template_mock.return_value = shared_service_template(template_name)

        response = await client.get(app.url_path_for(strings.API_GET_SHARED_SERVICE_TEMPLATE_BY_NAME, shared_service_template_name=template_name))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == template_name
        assert "description" in response.json()["required"]

    # GET /shared-service-templates/{service_template_name}
    @pytest.mark.parametrize("exception, expected_status", [
        (EntityDoesNotExist, status.HTTP_404_NOT_FOUND),
        (UnableToAccessDatabase, status.HTTP_503_SERVICE_UNAVAILABLE)
    ])
    @patch("api.routes.shared_service_templates.ResourceTemplateRepository.get_current_template")
    async def test_get_shared_service_template_by_name_returns_not_found_if_does_not_exist(self, get_current_template_mock, app, client, exception, expected_status):
        get_current_template_mock.side_effect = exception

        response = await client.get(app.url_path_for(strings.API_GET_SHARED_SERVICE_TEMPLATE_BY_NAME, shared_service_template_name="non-existent"))

        assert response.status_code == expected_status

    # POST /shared-service-templates/
    @patch("api.routes.shared_service_templates.ResourceTemplateRepository.create_template")
    @patch("api.routes.shared_service_templates.ResourceTemplateRepository.get_current_template")
    @patch("api.routes.shared_service_templates.ResourceTemplateRepository.get_template_by_name_and_version")
    async def test_when_creating_service_template_sets_additional_properties(self, get_template_by_name_and_version_mock, get_current_template_mock, create_template_mock, app, client, input_shared_service_template, basic_shared_service_template):
        get_template_by_name_and_version_mock.side_effect = EntityDoesNotExist
        get_current_template_mock.side_effect = EntityDoesNotExist
        create_template_mock.return_value = basic_shared_service_template

        response = await client.post(app.url_path_for(strings.API_CREATE_SHARED_SERVICE_TEMPLATES), json=input_shared_service_template.dict())

        expected_template = parse_obj_as(SharedServiceTemplateInResponse, enrich_shared_service_template(basic_shared_service_template))
        assert json.loads(response.text)["required"] == expected_template.dict(exclude_unset=True)["required"]
        assert json.loads(response.text)["properties"] == expected_template.dict(exclude_unset=True)["properties"]

    # POST /shared_services-templates
    @patch("api.routes.shared_service_templates.ResourceTemplateRepository.create_and_validate_template", side_effect=EntityVersionExist)
    async def test_version_exists_not_allowed(self, _, app, client, input_shared_service_template):
        response = await client.post(app.url_path_for(strings.API_CREATE_SHARED_SERVICE_TEMPLATES), json=input_shared_service_template.dict())

        assert response.status_code == status.HTTP_409_CONFLICT

    @patch("api.routes.workspace_service_templates.ResourceTemplateRepository.create_and_validate_template", side_effect=InvalidInput)
    async def test_creating_a_shared_service_template_raises_http_422_if_step_ids_are_duplicated(self, _, client, app, input_shared_service_template):
        response = await client.post(app.url_path_for(strings.API_CREATE_SHARED_SERVICE_TEMPLATES), json=input_shared_service_template.dict())

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
