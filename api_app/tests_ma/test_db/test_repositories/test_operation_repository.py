from unittest.mock import MagicMock
import uuid
import pytest
from mock import patch
from models.domain.operation import Status
from db.repositories.resources import ResourceRepository
from db.repositories.operations import OperationRepository
from tests_ma.test_api.test_routes.test_resource_helpers import FAKE_CREATE_TIMESTAMP

RESOURCE_ID = str(uuid.uuid4())
OPERATION_ID = str(uuid.uuid4())


@pytest.fixture
def operations_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield OperationRepository(cosmos_client_mock)


@pytest.fixture
def resource_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield ResourceRepository(cosmos_client_mock)


@patch("db.repositories.operations.OperationRepository.get_timestamp", return_value=FAKE_CREATE_TIMESTAMP)
@patch("db.repositories.operations.OperationRepository.create_operation_id", return_value=OPERATION_ID)
def test_create_operation_steps_from_multi_step_template(_, __, resource_repo, test_user, multi_step_operation, operations_repo, multi_step_resource_template, basic_shared_service):

    expected_op = multi_step_operation
    expected_op.id = OPERATION_ID

    expected_op.status = Status.AwaitingDeployment
    expected_op.message = "This resource is waiting to be deployed"

    operations_repo.save_item = MagicMock()
    resource_repo.get_operating_resource_by_template_name = MagicMock(return_value=basic_shared_service)
    operation = operations_repo.create_operation_item(
        resource_id="resource-id",
        action="install",
        resource_path="/workspaces/resource-id",
        resource_version=0,
        user=test_user,
        resource_template=multi_step_resource_template,
        resource_repo=resource_repo
    )

    assert operation.dict() == expected_op.dict()
