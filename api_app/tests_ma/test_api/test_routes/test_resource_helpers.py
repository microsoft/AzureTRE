import uuid
import pytest
from mock import patch, MagicMock

from fastapi import HTTPException, status

from api.routes.resource_helpers import save_and_deploy_resource, send_uninstall_message

from db.repositories.resources import ResourceRepository
from db.repositories.operations import OperationRepository
from models.domain.operation import Operation, Status
from models.domain.resource import RequestAction, ResourceType
from models.domain.workspace import Workspace


pytestmark = pytest.mark.asyncio


WORKSPACE_ID = '933ad738-7265-4b5f-9eae-a1a62928772e'


@pytest.fixture
def resource_repo() -> ResourceRepository:
    with patch("azure.cosmos.CosmosClient") as cosmos_client_mock:
        return ResourceRepository(cosmos_client_mock)


@pytest.fixture
def operations_repo() -> OperationRepository:
    with patch("azure.cosmos.CosmosClient") as cosmos_client_mock:
        return OperationRepository(cosmos_client_mock)


def sample_resource(workspace_id=WORKSPACE_ID, auth_info: dict = {}):
    workspace = Workspace(
        id=workspace_id,
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties={
            "app_id": "12345"
        },
        resourcePath=f'/workspaces/{workspace_id}'
    )
    if auth_info:
        workspace.authInformation = auth_info
    return workspace


def sample_resource_operation(resource_id: str, operation_id: str):
    operation = Operation(
        id=operation_id,
        resourceId=resource_id,
        resourcePath=f'/workspaces/{resource_id}',
        resourceVersion=0,
        action="install",
        message="test",
        Status=Status.Deployed,
        createdWhen=1642611942.423857,
        updatedWhen=1642611942.423857
    )
    return operation


class TestResourceHelpers:
    @patch("api.routes.resource_helpers.send_resource_request_message")
    async def test_save_and_deploy_resource_saves_item(self, _, resource_repo, operations_repo):
        resource = sample_resource()
        operation = sample_resource_operation(resource_id=resource.id, operation_id=str(uuid.uuid4()))

        resource_repo.save_item = MagicMock(return_value=None)
        operations_repo.create_operation_item = MagicMock(return_value=operation)

        await save_and_deploy_resource(resource, resource_repo, operations_repo)

        resource_repo.save_item.assert_called_once_with(resource)

    async def test_save_and_deploy_resource_raises_503_if_save_to_db_fails(self, resource_repo, operations_repo):
        resource = sample_resource()
        resource_repo.save_item = MagicMock(side_effect=Exception)

        with pytest.raises(HTTPException) as ex:
            await save_and_deploy_resource(resource, resource_repo, operations_repo)
        assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=None)
    async def test_save_and_deploy_resource_sends_resource_request_message(self, send_resource_request_mock, resource_repo, operations_repo):
        resource = sample_resource()
        operation = sample_resource_operation(resource_id=resource.id, operation_id=str(uuid.uuid4()))

        resource_repo.save_item = MagicMock(return_value=None)
        operations_repo.create_operations_item = MagicMock(return_value=operation)

        await save_and_deploy_resource(resource, resource_repo, operations_repo)

        send_resource_request_mock.assert_called_once_with(resource, operations_repo, RequestAction.Install)

    @patch("api.routes.resource_helpers.send_resource_request_message", side_effect=Exception)
    async def test_save_and_deploy_resource_raises_503_if_send_request_fails(self, _, resource_repo, operations_repo):
        resource = sample_resource()
        resource_repo.save_item = MagicMock(return_value=None)
        resource_repo.delete_item = MagicMock(return_value=None)

        with pytest.raises(HTTPException) as ex:
            await save_and_deploy_resource(resource, resource_repo, operations_repo)
        assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.resource_helpers.send_resource_request_message", side_effect=Exception)
    async def test_save_and_deploy_resource_deletes_item_from_db_if_send_request_fails(self, _, resource_repo, operations_repo):
        resource = sample_resource()

        resource_repo.save_item = MagicMock(return_value=None)
        resource_repo.delete_item = MagicMock(return_value=None)
        operations_repo.create_operation_item = MagicMock(return_value=None)

        with pytest.raises(HTTPException):
            await save_and_deploy_resource(resource, resource_repo, operations_repo)

        resource_repo.delete_item.assert_called_once_with(resource.id)

    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=None)
    @patch("api.routes.workspaces.OperationRepository")
    async def test_send_uninstall_message_sends_uninstall_message(self, operations_repo, send_request_mock):
        resource = sample_resource()
        await send_uninstall_message(resource, operations_repo, ResourceType.Workspace)

        send_request_mock.assert_called_once_with(resource, operations_repo, RequestAction.UnInstall)

    @patch("api.routes.resource_helpers.send_resource_request_message", side_effect=Exception)
    @patch("api.routes.workspaces.OperationRepository")
    async def test_send_uninstall_message_raises_503_on_service_bus_exception(self, operations_repo, _):
        with pytest.raises(HTTPException) as ex:
            await send_uninstall_message(sample_resource(), operations_repo, ResourceType.Workspace)
        assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
