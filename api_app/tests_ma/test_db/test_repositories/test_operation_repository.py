from unittest.mock import AsyncMock
import uuid
import pytest_asyncio
import pytest
from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosHttpResponseError
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
    with patch("api.dependencies.database.Database.get_container_proxy", return_value=None):
        operations_repo = await OperationRepository.create()
        yield operations_repo


@pytest_asyncio.fixture
async def resource_repo():
    with patch("api.dependencies.database.Database.get_container_proxy", return_value=None):
        resource_repo = await ResourceRepository.create()
        yield resource_repo


@pytest_asyncio.fixture
async def resource_template_repo():
    with patch("api.dependencies.database.Database.get_container_proxy", return_value=None):
        resource_template_repo = await ResourceTemplateRepository.create()
        yield resource_template_repo


@patch("uuid.uuid4", side_effect=["random-uuid-1", "random-uuid-2", "random-uuid-3"])
@patch("db.repositories.operations.OperationRepository.get_timestamp", return_value=FAKE_CREATE_TIMESTAMP)
@patch("db.repositories.operations.OperationRepository.create_operation_id", return_value=OPERATION_ID)
async def test_create_operation_steps_from_multi_step_template(
    _,
    __,
    ___,
    resource_repo,
    test_user,
    multi_step_operation,
    operations_repo,
    basic_shared_service,
    resource_template_repo,
    multi_step_resource_template,
):

    expected_op = multi_step_operation
    expected_op.id = OPERATION_ID

    expected_op.status = Status.AwaitingDeployment
    expected_op.message = "This resource is waiting to be deployed"

    operations_repo.save_item_dict = AsyncMock()
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
        resource_template_repo=resource_template_repo,
    )

    assert operation.model_dump() == expected_op.model_dump()
    # The same write records the first step message until the API sends it.
    document = operations_repo.save_item_dict.await_args.args[0]
    assert document == {
        **expected_op.model_dump(),
        "pendingDispatch": {
            "stepId": "random-uuid-1",
            "messageId": f"{OPERATION_ID}:random-uuid-1",
            "createdWhen": FAKE_CREATE_TIMESTAMP,
        },
    }


@pytest_asyncio.fixture
async def operations_container():
    container = AsyncMock()
    with patch("api.dependencies.database.Database.get_container_proxy", return_value=container):
        operations_repo = await OperationRepository.create()
        yield operations_repo, container


async def test_claim_pending_dispatch_uses_the_etag_of_the_read_document(operations_container):
    operations_repo, container = operations_container

    assert await operations_repo.claim_pending_dispatch({"id": OPERATION_ID, "_etag": "etag"})

    kwargs = container.patch_item.await_args.kwargs
    assert kwargs["item"] == OPERATION_ID
    assert kwargs["etag"] == "etag"
    assert kwargs["match_condition"] == MatchConditions.IfNotModified
    assert kwargs["patch_operations"][0]["path"] == "/pendingDispatch/createdWhen"


async def test_claim_pending_dispatch_returns_false_after_another_write(operations_container):
    operations_repo, container = operations_container
    container.patch_item.side_effect = CosmosHttpResponseError(status_code=412)

    assert not await operations_repo.claim_pending_dispatch({"id": OPERATION_ID, "_etag": "etag"})


async def test_claim_pending_dispatch_raises_other_errors(operations_container):
    operations_repo, container = operations_container
    container.patch_item.side_effect = CosmosHttpResponseError(status_code=503)

    with pytest.raises(CosmosHttpResponseError):
        await operations_repo.claim_pending_dispatch({"id": OPERATION_ID, "_etag": "etag"})


async def test_clear_pending_dispatch_removes_only_the_named_message(operations_container):
    operations_repo, container = operations_container
    message_id = f"{OPERATION_ID}:step-1"

    await operations_repo.clear_pending_dispatch(OPERATION_ID, message_id)

    kwargs = container.patch_item.await_args.kwargs
    assert kwargs["patch_operations"] == [{"op": "remove", "path": "/pendingDispatch"}]
    assert kwargs["filter_predicate"] == f"FROM c WHERE c.pendingDispatch.messageId = '{message_id}'"

    # Another writer already removed the entry or replaced it.
    container.patch_item.side_effect = CosmosHttpResponseError(status_code=412)
    await operations_repo.clear_pending_dispatch(OPERATION_ID, message_id)


async def test_clear_pending_dispatch_rejects_other_message_ids(operations_container):
    operations_repo, container = operations_container

    with pytest.raises(ValueError):
        await operations_repo.clear_pending_dispatch(OPERATION_ID, "x' OR '1'='1:step")
    container.patch_item.assert_not_awaited()


async def test_pending_dispatch_query_uses_the_send_time(operations_container):
    operations_repo, _ = operations_container
    operations_repo.query = AsyncMock(return_value=[])

    await operations_repo.get_operations_with_pending_dispatch(100.0)

    kwargs = operations_repo.query.await_args.kwargs
    assert "c.pendingDispatch.createdWhen < @sentBefore" in kwargs["query"]
    assert kwargs["parameters"] == [{"name": "@sentBefore", "value": 100.0}]
