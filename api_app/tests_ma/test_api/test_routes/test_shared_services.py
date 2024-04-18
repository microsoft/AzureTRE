import random
from unittest.mock import AsyncMock
import uuid
import pytest
from mock import patch

from fastapi import status
from models.domain.resource import ResourceHistoryItem

from tests_ma.test_api.conftest import create_admin_user, create_test_user
from .test_workspaces import FAKE_CREATE_TIMESTAMP, FAKE_UPDATE_TIMESTAMP, OPERATION_ID, sample_resource_operation

from db.errors import EntityDoesNotExist
from models.domain.shared_service import SharedService
from resources import strings
from services.authentication import get_current_admin_user, get_current_tre_user_or_tre_admin
from azure.cosmos.exceptions import CosmosAccessConditionFailedError


pytestmark = pytest.mark.asyncio

SHARED_SERVICE_ID = 'abcad738-7265-4b5f-9eae-a1a62928772e'
ETAG = "some-etag-value"


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


def sample_resource_history(history_length, shared_service_id=SHARED_SERVICE_ID) -> ResourceHistoryItem:
    resource_history = []
    user = create_test_user()

    for version in range(history_length):
        resource_history_item = ResourceHistoryItem(
            id=str(uuid.uuid4()),
            resourceId=shared_service_id,
            isEnabled=True,
            resourceVersion=version,
            templateVersion="template_version",
            properties={
                'display_name': 'initial display name',
                'description': 'initial description',
                'computed_prop': 'computed_val'
            },
            updatedWhen=FAKE_CREATE_TIMESTAMP,
            user=user
        )
        resource_history.append(resource_history_item)
    return resource_history


class TestSharedServiceRoutesThatDontRequireAdminRigths:
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_non_admin_user(self, app, non_admin_user):
        with patch('services.aad_authentication.AzureADAuthorization._get_user_from_token', return_value=non_admin_user()):
            app.dependency_overrides[get_current_tre_user_or_tre_admin] = non_admin_user
            yield
            app.dependency_overrides = {}

    # [GET] /shared-services
    @patch("api.routes.shared_services.SharedServiceRepository.get_active_shared_services", return_value=None)
    @patch("api.routes.shared_services.enrich_resource_with_available_upgrades", return_value=None)
    async def test_get_shared_services_returns_list_of_shared_services_for_user(self, _, get_active_shared_services_mock, app, client):
        shared_services = [sample_shared_service()]
        get_active_shared_services_mock.return_value = shared_services

        response = await client.get(app.url_path_for(strings.API_GET_ALL_SHARED_SERVICES))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["sharedServices"][0]["id"] == sample_shared_service().id

        # check that as a user we only get the restricted resource model
        assert 'private_field_1' not in response.json()["sharedServices"][0]["properties"]
        assert 'private_field_2' not in response.json()["sharedServices"][0]["properties"]

    # [GET] /shared-services/<shared-service-id>
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", return_value=sample_shared_service())
    @patch("api.routes.shared_services.enrich_resource_with_available_upgrades", return_value=None)
    async def test_get_shared_service_returns_shared_service_result_for_user(self, _, get_shared_service_mock, app, client):
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

    # [GET] /shared-services
    @patch("api.routes.shared_services.SharedServiceRepository.get_active_shared_services", return_value=None)
    @patch("api.routes.shared_services.enrich_resource_with_available_upgrades", return_value=None)
    async def test_get_shared_services_returns_list_of_shared_services_for_admin_user(self, _, get_active_shared_services_mock, app, client):
        shared_services = [sample_shared_service()]
        get_active_shared_services_mock.return_value = shared_services

        response = await client.get(app.url_path_for(strings.API_GET_ALL_SHARED_SERVICES))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["sharedServices"][0]["id"] == sample_shared_service().id

        # check that as a user we only get the restricted resource model
        assert response.json()["sharedServices"][0]["properties"]["private_field_1"] == "value_1"
        assert response.json()["sharedServices"][0]["properties"]["private_field_2"] == "value_2"

    # [GET] /shared-services/{shared_service_id}
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", return_value=sample_shared_service())
    @patch("api.routes.shared_services.enrich_resource_with_available_upgrades", return_value=None)
    async def test_get_shared_service_returns_shared_service_result(self, _, get_shared_service_mock, app, client):
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

        response = await client.patch(app.url_path_for(strings.API_UPDATE_SHARED_SERVICE, shared_service_id=SHARED_SERVICE_ID), json=shared_service_patch, headers={"etag": ETAG})
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
    @patch("api.routes.shared_services.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.shared_services.SharedServiceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", return_value=sample_shared_service(SHARED_SERVICE_ID))
    @patch("api.routes.shared_services.ResourceTemplateRepository.get_template_by_name_and_version", return_value=None)
    @patch("api.routes.shared_services.SharedServiceRepository.update_item_with_etag", return_value=sample_shared_service())
    @patch("api.routes.shared_services.send_resource_request_message", return_value=sample_resource_operation(resource_id=SHARED_SERVICE_ID, operation_id=OPERATION_ID))
    async def test_patch_shared_service_patches_shared_service(self, _, update_item_mock, __, ___, ____, _____, app, client):
        shared_service_patch = {"isEnabled": False}

        modified_shared_service = sample_shared_service()
        modified_shared_service.isEnabled = False
        modified_shared_service.resourceVersion = 1
        modified_shared_service.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_shared_service.user = create_admin_user()

        response = await client.patch(app.url_path_for(strings.API_UPDATE_SHARED_SERVICE, shared_service_id=SHARED_SERVICE_ID), json=shared_service_patch, headers={"etag": ETAG})
        update_item_mock.assert_called_once_with(modified_shared_service, ETAG)

        assert response.status_code == status.HTTP_202_ACCEPTED

    # [PATCH] /shared-services/{shared_service_id}
    @patch("api.routes.shared_services.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.shared_services.SharedServiceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", return_value=sample_shared_service(SHARED_SERVICE_ID))
    @patch("api.routes.shared_services.ResourceTemplateRepository.get_template_by_name_and_version", return_value=sample_shared_service())
    @patch("api.routes.shared_services.SharedServiceRepository.update_item_with_etag", return_value=sample_shared_service())
    @patch("api.routes.shared_services.send_resource_request_message", return_value=sample_resource_operation(resource_id=SHARED_SERVICE_ID, operation_id=OPERATION_ID))
    async def test_patch_shared_service_with_upgrade_minor_version_patches_shared_service(self, _, update_item_mock, __, ___, ____, _____, app, client):
        shared_service_patch = {"templateVersion": "0.2.0"}

        modified_shared_service = sample_shared_service()
        modified_shared_service.isEnabled = True
        modified_shared_service.resourceVersion = 1
        modified_shared_service.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_shared_service.user = create_admin_user()
        modified_shared_service.templateVersion = "0.2.0"

        response = await client.patch(app.url_path_for(strings.API_UPDATE_SHARED_SERVICE, shared_service_id=SHARED_SERVICE_ID), json=shared_service_patch, headers={"etag": ETAG})
        update_item_mock.assert_called_once_with(modified_shared_service, ETAG)

        assert response.status_code == status.HTTP_202_ACCEPTED

    # [PATCH] /shared-services/{shared_service_id}
    @patch("api.routes.shared_services.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.shared_services.SharedServiceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", return_value=sample_shared_service(SHARED_SERVICE_ID))
    @patch("api.routes.shared_services.ResourceTemplateRepository.get_template_by_name_and_version", return_value=sample_shared_service())
    @patch("api.routes.shared_services.SharedServiceRepository.update_item_with_etag", return_value=sample_shared_service())
    @patch("api.routes.shared_services.send_resource_request_message", return_value=sample_resource_operation(resource_id=SHARED_SERVICE_ID, operation_id=OPERATION_ID))
    async def test_patch_shared_service_with_upgrade_major_version_and_force_update_patches_shared_service(self, _, update_item_mock, __, ___, ____, _____, app, client):
        shared_service_patch = {"templateVersion": "2.0.0"}

        modified_shared_service = sample_shared_service()
        modified_shared_service.isEnabled = True
        modified_shared_service.resourceVersion = 1
        modified_shared_service.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_shared_service.user = create_admin_user()
        modified_shared_service.templateVersion = "2.0.0"

        response = await client.patch(app.url_path_for(strings.API_UPDATE_SHARED_SERVICE, shared_service_id=SHARED_SERVICE_ID) + "?force_version_update=True", json=shared_service_patch, headers={"etag": ETAG})
        update_item_mock.assert_called_once_with(modified_shared_service, ETAG)

        assert response.status_code == status.HTTP_202_ACCEPTED

    # [PATCH] /shared-services/{shared_service_id}
    @patch("api.routes.shared_services.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.shared_services.SharedServiceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", return_value=sample_shared_service(SHARED_SERVICE_ID))
    @patch("api.routes.shared_services.ResourceTemplateRepository.get_template_by_name_and_version", return_value=None)
    @patch("api.routes.shared_services.SharedServiceRepository.update_item_with_etag", return_value=sample_shared_service())
    @patch("api.routes.shared_services.send_resource_request_message", return_value=sample_resource_operation(resource_id=SHARED_SERVICE_ID, operation_id=OPERATION_ID))
    async def test_patch_shared_service_with_upgrade_major_version_returns_bad_request(self, _, update_item_mock, __, ___, ____, _____, app, client):
        shared_service_patch = {"templateVersion": "2.0.0"}

        modified_shared_service = sample_shared_service()
        modified_shared_service.isEnabled = True
        modified_shared_service.resourceVersion = 1
        modified_shared_service.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_shared_service.user = create_admin_user()

        response = await client.patch(app.url_path_for(strings.API_UPDATE_SHARED_SERVICE, shared_service_id=SHARED_SERVICE_ID), json=shared_service_patch, headers={"etag": ETAG})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.text == 'Attempt to upgrade from 0.1.0 to 2.0.0 denied. major version upgrade is not allowed.'

    # [PATCH] /shared-services/{shared_service_id}
    @patch("api.routes.shared_services.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.shared_services.SharedServiceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", return_value=sample_shared_service(SHARED_SERVICE_ID))
    @patch("api.routes.shared_services.ResourceTemplateRepository.get_template_by_name_and_version", return_value=None)
    @patch("api.routes.shared_services.SharedServiceRepository.update_item_with_etag", return_value=sample_shared_service())
    @patch("api.routes.shared_services.send_resource_request_message", return_value=sample_resource_operation(resource_id=SHARED_SERVICE_ID, operation_id=OPERATION_ID))
    async def test_patch_shared_service_with_downgrade_version_returns_bad_request(self, _, update_item_mock, __, ___, ____, _____, app, client):
        shared_service_patch = {"templateVersion": "0.0.1"}

        modified_shared_service = sample_shared_service()
        modified_shared_service.isEnabled = True
        modified_shared_service.resourceVersion = 1
        modified_shared_service.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_shared_service.user = create_admin_user()

        response = await client.patch(app.url_path_for(strings.API_UPDATE_SHARED_SERVICE, shared_service_id=SHARED_SERVICE_ID), json=shared_service_patch, headers={"etag": ETAG})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.text == 'Attempt to downgrade from 0.1.0 to 0.0.1 denied. version downgrade is not allowed.'

    # [GET] /shared-services/{shared_service_id}/history
    @patch("api.routes.shared_services.ResourceHistoryRepository.get_resource_history_by_resource_id")
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id")
    async def test_get_shared_service_history_returns_shared_service_history_result(self, get_shared_service_mock, get_resource_history_mock, app, client):
        sample_guid = str(uuid.uuid4())
        sample_history_length = random.randint(1, 10)
        shared_service = sample_shared_service(shared_service_id=sample_guid)
        shared_service_history = sample_resource_history(history_length=sample_history_length, shared_service_id=sample_guid)
        get_shared_service_mock.return_value = shared_service
        get_resource_history_mock.return_value = shared_service_history

        response = await client.get(
            app.url_path_for(strings.API_GET_RESOURCE_HISTORY, shared_service_id=SHARED_SERVICE_ID))

        assert response.status_code == status.HTTP_200_OK
        obj = response.json()["resource_history"]
        assert len(obj) == sample_history_length
        for item in obj:
            assert item["resourceId"] == shared_service.id

    # [GET] /shared-services/{shared_service_id}/history
    @patch("api.routes.shared_services.ResourceHistoryRepository.get_resource_history_by_resource_id")
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", return_value=sample_shared_service())
    async def test_get_shared_service_history_returns_empty_list_when_no_history(self, _, get_resource_history_mock, app, client):
        get_resource_history_mock.return_value = []

        response = await client.get(
            app.url_path_for(strings.API_GET_RESOURCE_HISTORY, shared_service_id=SHARED_SERVICE_ID))

        assert response.status_code == status.HTTP_200_OK
        obj = response.json()["resource_history"]
        assert len(obj) == 0

    # [PATCH] /shared-services/{shared_service_id}
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", return_value=sample_shared_service(SHARED_SERVICE_ID))
    async def test_patch_shared_service_with_invalid_field_returns_422(self, _, app, client):
        shared_service_patch = {"fakeField": "someValue", "templateVersion": "0.2.0"}

        response = await client.patch(app.url_path_for(strings.API_UPDATE_SHARED_SERVICE, shared_service_id=SHARED_SERVICE_ID), json=shared_service_patch, headers={"etag": ETAG})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.text == "[{'loc': ('body', 'fakeField'), 'msg': 'extra fields not permitted', 'type': 'value_error.extra'}]"
