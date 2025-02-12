import pytest
from fastapi import status
from mock import patch

from resources import strings
from services.authentication import get_current_tre_user_or_tre_admin


pytestmark = pytest.mark.asyncio


class TestRequestsThatDontRequireAdminRigths:
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_non_admin_user(self, app, non_admin_user):
        with patch('services.aad_authentication.AzureADAuthorization._get_user_from_token', return_value=non_admin_user()):
            app.dependency_overrides[get_current_tre_user_or_tre_admin] = non_admin_user
            yield
            app.dependency_overrides = {}

    # [GET] /requests/ - get_requests
    @patch("api.routes.airlock.AirlockRequestRepository.get_airlock_requests", return_value=[])
    async def test_get_all_requests_returns_200(self, _, app, client):
        response = await client.get(app.url_path_for(strings.API_LIST_REQUESTS))
        assert response.status_code == status.HTTP_200_OK

    @patch("api.routes.airlock.AirlockRequestRepository.get_airlock_requests_for_airlock_manager")
    async def test_get_airlock_manager_requests_returns_200(self, mock_get_airlock_requests_for_airlock_manager, app, client):
        mock_get_airlock_requests_for_airlock_manager.return_value = []
        response = await client.get(app.url_path_for(strings.API_LIST_REQUESTS), params={"airlock_manager": True})

        assert response.status_code == status.HTTP_200_OK
        mock_get_airlock_requests_for_airlock_manager.assert_called_once()

    @patch("api.routes.airlock.AirlockRequestRepository.get_airlock_requests", side_effect=Exception("Internal Server Error"))
    async def test_get_all_requests_returns_500(self, _, app, client):
        response = await client.get(app.url_path_for(strings.API_LIST_REQUESTS))
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch("api.routes.airlock.AirlockRequestRepository.get_airlock_requests_for_airlock_manager", side_effect=Exception("Internal Server Error"))
    async def test_get_airlock_manager_requests_returns_500(self, _, app, client):
        response = await client.get(app.url_path_for(strings.API_LIST_REQUESTS), params={"airlock_manager": True})
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
