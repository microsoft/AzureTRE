
import pytest
from mock import patch, MagicMock

from db.repositories.shared_services import SharedServiceRepository


SHARED_SERVICE_ID = "000000d3-82da-4bfc-b6e9-9a7853ef753e"


@pytest.fixture
def shared_service_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield SharedServiceRepository(cosmos_client_mock)


def test_get_active_shared_services_for_shared_queries_db(shared_service_repo):
    shared_service_repo.query = MagicMock()
    shared_service_repo.query.return_value = []

    shared_service_repo.get_active_shared_services(SHARED_SERVICE_ID)

    shared_service_repo.query.assert_called_once_with(query=SharedServiceRepository.active_shared_services_query(SHARED_SERVICE_ID))
