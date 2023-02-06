from unittest.mock import AsyncMock
import uuid
import pytest_asyncio
import pytest
from mock import patch
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.operation import Status
from db.repositories.resources import ResourceRepository
from db.repositories.operations import OperationRepository
from tests_ma.test_api.test_routes.test_resource_helpers import FAKE_CREATE_TIMESTAMP

RESOURCE_ID = str(uuid.uuid4())
OPERATION_ID = str(uuid.uuid4())


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def operations_repo():
    with patch('db.repositories.base.BaseRepository._get_container', return_value=None):
        with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
            operations_repo = await OperationRepository.create(cosmos_client_mock)
            yield operations_repo


@pytest_asyncio.fixture
async def resource_repo():
    with patch('db.repositories.base.BaseRepository._get_container', return_value=None):
        with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
            resource_repo = await ResourceRepository.create(cosmos_client_mock)
            yield resource_repo


@pytest_asyncio.fixture
async def resource_template_repo():
    with patch('db.repositories.base.BaseRepository._get_container', return_value=None):
        with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
            resource_template_repo = await ResourceTemplateRepository.create(cosmos_client_mock)
            yield resource_template_repo


@patch("db.repositories.operations.OperationRepository.get_timestamp", return_value=FAKE_CREATE_TIMESTAMP)
@patch("db.repositories.operations.OperationRepository.create_operation_id", return_value=OPERATION_ID)
async def test_create_operation_steps_from_multi_step_template(_, __, resource_repo, test_user, multi_step_operation, operations_repo, basic_shared_service, resource_template_repo, multi_step_resource_template):

    expected_op = multi_step_operation
    expected_op.id = OPERATION_ID

    expected_op.status = Status.AwaitingDeployment
    expected_op.message = "This resource is waiting to be deployed"

    operations_repo.save_item = AsyncMock()
    resource_repo.get_active_resource_by_template_name = AsyncMock(return_value=basic_shared_service)
    resource_template_repo.get_template_by_name_and_version = AsyncMock(return_value=multi_step_resource_template)

    operation = await operations_repo.create_operation_item(
        resource_id="resource-id",
        resource_list=[basic_shared_service.__dict__],
        action="install",
        resource_path="/workspaces/resource-id",
        resource_version=0,
        user=test_user,
        resource_repo=resource_repo,
        resource_template_repo=resource_template_repo

    )

    assert operation.dict() == expected_op.dict()
