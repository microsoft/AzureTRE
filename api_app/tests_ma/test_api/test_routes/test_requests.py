import pytest
from fastapi import status
from mock import patch

from models.domain.airlock_request import AirlockRequestStatus, AirlockRequestType
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
    @patch("api.routes.requests.AirlockRequestRepository.get_airlock_requests", return_value=[])
    async def test_get_all_requests_returns_200(self, _, app, client):
        response = await client.get(app.url_path_for(strings.API_LIST_REQUESTS))
        assert response.status_code == status.HTTP_200_OK

    @patch("api.routes.requests.AirlockRequestRepository.get_airlock_requests_for_airlock_manager")
    async def test_get_airlock_manager_requests_returns_200(self, mock_get_airlock_requests_for_airlock_manager, app, client):
        mock_get_airlock_requests_for_airlock_manager.return_value = []
        response = await client.get(app.url_path_for(strings.API_LIST_REQUESTS), params={"airlock_manager": True})

        assert response.status_code == status.HTTP_200_OK
        mock_get_airlock_requests_for_airlock_manager.assert_called_once()

    @patch("api.routes.requests.AirlockRequestRepository.get_airlock_requests", side_effect=Exception("Internal Server Error"))
    async def test_get_all_requests_returns_500(self, _, app, client):
        response = await client.get(app.url_path_for(strings.API_LIST_REQUESTS))
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch("api.routes.requests.AirlockRequestRepository.get_airlock_requests_for_airlock_manager", side_effect=Exception("Internal Server Error"))
    async def test_get_airlock_manager_requests_returns_500(self, _, app, client):
        response = await client.get(app.url_path_for(strings.API_LIST_REQUESTS), params={"airlock_manager": True})
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch("api.routes.requests.AirlockRequestRepository.get_airlock_requests", return_value=[{"id": "1", "status": AirlockRequestStatus.InReview}])
    async def test_get_requests_with_status_filter_returns_correct_results(self, mock_get_airlock_requests, app, client):
        response = await client.get(app.url_path_for(strings.API_LIST_REQUESTS), params={"status": AirlockRequestStatus.InReview})

        assert response.status_code == status.HTTP_200_OK
        mock_get_airlock_requests.assert_called_once_with(
            creator_user_id='user-guid-here', type=None, status=AirlockRequestStatus.InReview, order_by=None, order_ascending=True
        )
        assert len(response.json()) == 1
        assert response.json()[0]["status"] == AirlockRequestStatus.InReview

    @patch("api.routes.requests.AirlockRequestRepository.get_airlock_requests_for_airlock_manager", return_value=[{"id": "2", "status": AirlockRequestStatus.InReview}])
    async def test_get_requests_with_airlock_manager_filter_returns_correct_results(self, mock_get_airlock_requests_for_airlock_manager, app, client):
        response = await client.get(app.url_path_for(strings.API_LIST_REQUESTS), params={"airlock_manager": True})

        assert response.status_code == status.HTTP_200_OK
        mock_get_airlock_requests_for_airlock_manager.assert_called_once_with(
            user_id='user-guid-here', type=None, status=None, order_by=None, order_ascending=True
        )
        assert len(response.json()) == 1
        assert response.json()[0]["status"] == AirlockRequestStatus.InReview

    @patch("api.routes.requests.AirlockRequestRepository.get_airlock_requests_for_airlock_manager")
    async def test_get_airlock_manager_requests_with_all_parameters(self, mock_get_airlock_manager, app, client):
        """Test that airlock manager requests are called with all expected parameters"""
        mock_get_airlock_manager.return_value = []

        # Test with all query parameters
        response = await client.get(
            app.url_path_for(strings.API_LIST_REQUESTS),
            params={
                "airlock_manager": True,
                "type": AirlockRequestType.Import,
                "status": AirlockRequestStatus.InReview,
                "order_by": "updatedWhen",
                "order_ascending": False
            }
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify the method was called with exactly the expected parameters
        mock_get_airlock_manager.assert_called_once_with(
            user_id='user-guid-here',
            type=AirlockRequestType.Import,
            status=AirlockRequestStatus.InReview,
            order_by="updatedWhen",
            order_ascending=False
        )

    @patch("api.routes.requests.AirlockRequestRepository.get_airlock_requests_for_airlock_manager")
    async def test_airlock_manager_method_signature_compatibility(self, mock_get_airlock_manager, app, client):
        """Test that the airlock manager method can handle the parameters passed from the API route"""
        mock_get_airlock_manager.return_value = []

        # This should not raise any TypeError about missing arguments
        response = await client.get(
            app.url_path_for(strings.API_LIST_REQUESTS),
            params={
                "airlock_manager": True,
                "order_by": "updatedWhen",
                "order_ascending": False
            }
        )

        # If there's a missing argument issue, this test will fail with a 500 error
        # instead of the expected 200
        assert response.status_code == status.HTTP_200_OK

        # Verify the method was called with the correct arguments
        mock_get_airlock_manager.assert_called_once_with(
            user_id='user-guid-here',
            type=None,
            status=None,
            order_by="updatedWhen",
            order_ascending=False
        )
