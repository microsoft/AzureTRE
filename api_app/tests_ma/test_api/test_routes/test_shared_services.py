import copy
import uuid
import pytest
from mock import patch

from fastapi import status

from tests_ma.test_api.conftest import create_admin_user
from .test_workspaces import FAKE_CREATE_TIMESTAMP, FAKE_UPDATE_TIMESTAMP, OPERATION_ID, sample_resource_operation

from db.errors import EntityDoesNotExist
from models.domain.shared_service import SharedService
from resources import strings
from services.authentication import get_current_admin_user, get_current_tre_user_or_tre_admin
from azure.cosmos.exceptions import CosmosAccessConditionFailedError
from models.domain.resource import ResourceHistoryItem


pytestmark = pytest.mark.asyncio


SHARED_SERVICE_ID = 'abcad738-7265-4b5f-9eae-a1a62928772e'


@pytest.fixture
def shared_service_input():
    return {
        "templateName": "test-shared-service",
        "properties": {
            "display_name": "display"
        }
    }


def sample_shared_service(shared_service_id=SHARED_SERVICE_ID):
    return SharedService(
        id=shared_service_id,
        templateName="tre-shared-service-base",
        templateVersion="0.1.0",
        etag="",
        properties={
            'display_name': 'A display name',
            'description': 'desc here',
            'overview': 'overview here',
            'private_field_1': 'value_1',
            'private_field_2': 'value_2'
        },
        resourcePath=f'/shared-services/{shared_service_id}',
        updatedWhen=FAKE_CREATE_TIMESTAMP,
        user=create_admin_user()
    )


class TestSharedServiceRoutesThatDontRequireAdminRigths:
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_non_admin_user(self, app, non_admin_user):
        with patch('services.aad_authentication.AzureADAuthorization._get_user_from_token', return_value=non_admin_user()):
            app.dependency_overrides[get_current_tre_user_or_tre_admin] = non_admin_user
            yield
            app.dependency_overrides = {}

    # [GET] /shared-services
    @patch("api.routes.shared_services.SharedServiceRepository.get_active_shared_services", return_value=None)
    async def test_get_shared_services_returns_list_of_shared_services(self, get_active_shared_services_mock, app, client):
        shared_services = [sample_shared_service()]
        get_active_shared_services_mock.return_value = shared_services

        response = await client.get(app.url_path_for(strings.API_GET_ALL_SHARED_SERVICES))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["sharedServices"][0]["id"] == sample_shared_service().id

    # [GET] /shared-services/<shared-service-id>
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", return_value=sample_shared_service())
    async def test_get_shared_service_returns_shared_service_result_for_user(self, get_shared_service_mock, app, client):
        shared_service = sample_shared_service(shared_service_id=str(uuid.uuid4()))
        get_shared_service_mock.return_value = shared_service

        response = await client.get(
            app.url_path_for(strings.API_GET_SHARED_SERVICE_BY_ID, shared_service_id=SHARED_SERVICE_ID))

        assert response.status_code == status.HTTP_200_OK
        obj = response.json()["sharedService"]
        assert obj["id"] == shared_service.id

        # check that as a user we only get the restricted resource model
        assert 'private_field_1' not in obj["properties"]
        assert 'private_field_2' not in obj["properties"]


class TestSharedServiceRoutesThatRequireAdminRights:
    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, admin_user):
        with patch('services.aad_authentication.AzureADAuthorization._get_user_from_token', return_value=admin_user()):
            app.dependency_overrides[get_current_tre_user_or_tre_admin] = admin_user
            app.dependency_overrides[get_current_admin_user] = admin_user
            yield
            app.dependency_overrides = {}

    # [GET] /shared-services/{shared_service_id}
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", return_value=sample_shared_service())
    async def test_get_shared_service_returns_shared_service_result(self, get_shared_service_mock, app, client):
        shared_service = sample_shared_service(shared_service_id=str(uuid.uuid4()))
        get_shared_service_mock.return_value = shared_service

        response = await client.get(
            app.url_path_for(strings.API_GET_SHARED_SERVICE_BY_ID, shared_service_id=SHARED_SERVICE_ID))

        assert response.status_code == status.HTTP_200_OK
        obj = response.json()["sharedService"]
        assert obj["id"] == shared_service.id

        # check that as admin we DO get the full model
        assert obj["properties"]["private_field_1"] == "value_1"
        assert obj["properties"]["private_field_2"] == "value_2"

    # [GET] /shared-services/{shared_service_id}
    @patch("api.routes.shared_services.SharedServiceRepository.get_active_shared_services")
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", side_effect=EntityDoesNotExist)
    async def test_get_shared_service_raises_404_if_not_found(self, get_shared_service_mock, _, app, client):
        get_shared_service_mock.return_value = sample_shared_service(SHARED_SERVICE_ID)

        response = await client.get(
            app.url_path_for(strings.API_GET_SHARED_SERVICE_BY_ID, shared_service_id=SHARED_SERVICE_ID))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [PATCH] /shared-services/{shared_service_id}
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", side_effect=EntityDoesNotExist)
    async def test_patch_shared_service_returns_404_if_does_not_exist(self, _, app, client):
        response = await client.patch(app.url_path_for(strings.API_UPDATE_SHARED_SERVICE, shared_service_id=SHARED_SERVICE_ID), json='{"enabled": true}')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [PATCH] /shared-services/{shared_service_id}
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", return_value=sample_shared_service())
    @patch("api.dependencies.shared_services.SharedServiceRepository.patch_shared_service", side_effect=CosmosAccessConditionFailedError)
    async def test_patch_shared_service_returns_409_if_bad_etag(self, _, __, app, client):
        shared_service_patch = {"isEnabled": True}
        etag = "some-bad-etag-value"

        response = await client.patch(app.url_path_for(strings.API_UPDATE_SHARED_SERVICE, shared_service_id=SHARED_SERVICE_ID), json=shared_service_patch, headers={"etag": etag})
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.text == strings.ETAG_CONFLICT

    # [PATCH] /shared-services/{shared_service_id}
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", side_effect=EntityDoesNotExist)
    async def test_patch_shared_service_returns_422_if_invalid_id(self, get_shared_service_mock, app, client):
        shared_service_id = "IAmNotEvenAGUID!"
        get_shared_service_mock.return_value = sample_shared_service(shared_service_id)

        response = await client.patch(app.url_path_for(strings.API_UPDATE_SHARED_SERVICE, shared_service_id=shared_service_id), json={"enabled": True})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # [PATCH] /shared-services/{shared_service_id}
    @patch("api.routes.shared_services.SharedServiceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", return_value=sample_shared_service(SHARED_SERVICE_ID))
    @patch("api.routes.shared_services.ResourceTemplateRepository.get_template_by_name_and_version", return_value=None)
    @patch("api.routes.shared_services.SharedServiceRepository.update_item_with_etag", return_value=sample_shared_service())
    @patch("api.routes.shared_services.send_resource_request_message", return_value=sample_resource_operation(resource_id=SHARED_SERVICE_ID, operation_id=OPERATION_ID))
    async def test_patch_shared_service_patches_shared_service(self, _, update_item_mock, __, ___, ____, app, client):
        etag = "some-etag-value"
        shared_service_patch = {"isEnabled": False}

        modified_shared_service = sample_shared_service()
        modified_shared_service.isEnabled = False
        modified_shared_service.history = [ResourceHistoryItem(properties=copy.deepcopy(modified_shared_service.properties), isEnabled=True, resourceVersion=0, updatedWhen=FAKE_CREATE_TIMESTAMP, user=create_admin_user())]
        modified_shared_service.resourceVersion = 1
        modified_shared_service.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_shared_service.user = create_admin_user()

        response = await client.patch(app.url_path_for(strings.API_UPDATE_SHARED_SERVICE, shared_service_id=SHARED_SERVICE_ID), json=shared_service_patch, headers={"etag": etag})
        update_item_mock.assert_called_once_with(modified_shared_service, etag)

        assert response.status_code == status.HTTP_202_ACCEPTED
