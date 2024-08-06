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
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=None):
        operations_repo = await OperationRepository.create()
        yield operations_repo


@pytest_asyncio.fixture
async def resource_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=None):
        resource_repo = await ResourceRepository.create()
        yield resource_repo


@pytest_asyncio.fixture
async def resource_template_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=None):
        resource_template_repo = await ResourceTemplateRepository.create()
        yield resource_template_repo


@patch('uuid.uuid4', side_effect=["random-uuid-1", "random-uuid-2", "random-uuid-3"])
@patch("db.repositories.operations.OperationRepository.get_timestamp", return_value=FAKE_CREATE_TIMESTAMP)
@patch("db.repositories.operations.OperationRepository.create_operation_id", return_value=OPERATION_ID)
async def test_create_operation_steps_from_multi_step_template(_, __, ___, resource_repo, test_user, multi_step_operation, operations_repo, basic_shared_service, resource_template_repo, multi_step_resource_template):

    expected_op = multi_step_operation
    expected_op.id = OPERATION_ID

    expected_op.status = Status.AwaitingDeployment
    expected_op.message = "This resource is waiting to be deployed"

    operations_repo.save_item = AsyncMock()
    resource_repo.get_active_resource_by_template_name = AsyncMock(return_value=basic_shared_service)
    resource_template_repo.get_template_by_name_and_version = AsyncMock(return_value=multi_step_resource_template)

    operation = await operations_repo.create_operation_item(
        resource_id="59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
        resource_list=[basic_shared_service.__dict__],
        action="install",
        resource_path="/workspaces/59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
        resource_version=0,
        user=test_user,
        resource_repo=resource_repo,
        resource_template_repo=resource_template_repo

    )

    assert operation.dict() == expected_op.dict()
