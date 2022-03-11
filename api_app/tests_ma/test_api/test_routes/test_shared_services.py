import uuid
import pytest
from mock import patch

from fastapi import status

from db.errors import EntityDoesNotExist
from models.domain.shared_service import SharedService
from resources import strings
from services.authentication import get_current_admin_user


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
        properties={},
        resourcePath=f'/shared-services/{shared_service_id}'
    )


class TestSharedServiceRoutesThatRequireAdminRights:
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_admin_user(self, app, admin_user):
        app.dependency_overrides[get_current_admin_user] = admin_user
        yield
        app.dependency_overrides = {}

    # [GET] /shared-services
    @patch("api.routes.shared_services.SharedServiceRepository.get_active_shared_services",
           return_value=None)
    async def test_get_shared_services_returns_list_of_shared_services(self, get_active_shared_services_mock, app, client):
        shared_services = [sample_shared_service()]
        get_active_shared_services_mock.return_value = shared_services

        response = await client.get(app.url_path_for(strings.API_GET_ALL_SHARED_SERVICES))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["sharedServices"][0]["id"] == sample_shared_service().id

    # [GET] /shared-services/{shared_service_id}
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", return_value=sample_shared_service())
    async def test_get_shared_service_returns_shared_service_result(self, get_shared_service_mock, app, client):
        shared_service = sample_shared_service(shared_service_id=str(uuid.uuid4()))
        get_shared_service_mock.return_value = shared_service

        response = await client.get(
            app.url_path_for(strings.API_GET_SHARED_SERVICE_BY_ID, shared_service_id=SHARED_SERVICE_ID))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["sharedService"]["id"] == shared_service.id

    # [GET] /shared-services/{shared_service_id}
    @patch("api.routes.shared_services.SharedServiceRepository.get_active_shared_services")
    @patch("api.dependencies.shared_services.SharedServiceRepository.get_shared_service_by_id", side_effect=EntityDoesNotExist)
    async def test_get_shared_service_raises_404_if_not_found(self, _,
                                                              get_shared_service_mock,
                                                              app, client):
        get_shared_service_mock.return_value = sample_shared_service(SHARED_SERVICE_ID)

        response = await client.get(
            app.url_path_for(strings.API_GET_SHARED_SERVICE_BY_ID, shared_service_id=SHARED_SERVICE_ID))

        assert response.status_code == status.HTTP_404_NOT_FOUND
