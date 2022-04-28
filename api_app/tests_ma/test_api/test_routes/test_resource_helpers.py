import datetime
import uuid
import pytest
from mock import patch, MagicMock

from fastapi import HTTPException, status

from api.routes.resource_helpers import save_and_deploy_resource, send_uninstall_message
from tests_ma.test_api.conftest import create_test_user

from db.repositories.resources import ResourceRepository
from db.repositories.operations import OperationRepository
from models.domain.operation import Operation, Status
from models.domain.resource import RequestAction, ResourceType
from models.domain.workspace import Workspace


pytestmark = pytest.mark.asyncio


WORKSPACE_ID = '933ad738-7265-4b5f-9eae-a1a62928772e'
FAKE_CREATE_TIME = datetime.datetime(2021, 1, 1, 17, 5, 55)
FAKE_CREATE_TIMESTAMP: float = FAKE_CREATE_TIME.timestamp()
FAKE_UPDATE_TIME = datetime.datetime(2022, 1, 1, 17, 5, 55)
FAKE_UPDATE_TIMESTAMP: float = FAKE_UPDATE_TIME.timestamp()


@pytest.fixture
def resource_repo() -> ResourceRepository:
    with patch("azure.cosmos.CosmosClient") as cosmos_client_mock:
        return ResourceRepository(cosmos_client_mock)


@pytest.fixture
def operations_repo() -> OperationRepository:
    with patch("azure.cosmos.CosmosClient") as cosmos_client_mock:
        return OperationRepository(cosmos_client_mock)


def sample_resource(workspace_id=WORKSPACE_ID):
    workspace = Workspace(
        id=workspace_id,
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties={
            "client_id": "12345"
        },
        resourcePath=f'/workspaces/{workspace_id}',
        user=create_test_user(),
        updatedWhen=FAKE_CREATE_TIMESTAMP
    )
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
        createdWhen=FAKE_CREATE_TIMESTAMP,
        updatedWhen=FAKE_CREATE_TIMESTAMP,
        user=create_test_user()
    )
    return operation


class TestResourceHelpers:
    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @patch("api.routes.resource_helpers.send_resource_request_message")
    async def test_save_and_deploy_resource_saves_item(self, _, resource_template_repo, resource_repo, operations_repo, basic_resource_template):
        resource = sample_resource()
        operation = sample_resource_operation(resource_id=resource.id, operation_id=str(uuid.uuid4()))

        resource_repo.save_item = MagicMock(return_value=None)
        operations_repo.create_operation_item = MagicMock(return_value=operation)

        await save_and_deploy_resource(
            resource=resource,
            resource_repo=resource_repo,
            operations_repo=operations_repo,
            resource_template_repo=resource_template_repo,
            user=create_test_user(),
            resource_template=basic_resource_template)

        resource_repo.save_item.assert_called_once_with(resource)

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    async def test_save_and_deploy_resource_raises_503_if_save_to_db_fails(self, resource_template_repo, resource_repo, operations_repo, basic_resource_template):
        resource = sample_resource()
        resource_repo.save_item = MagicMock(side_effect=Exception)

        with pytest.raises(HTTPException) as ex:
            await save_and_deploy_resource(
                resource=resource,
                resource_repo=resource_repo,
                operations_repo=operations_repo,
                resource_template_repo=resource_template_repo,
                user=create_test_user(),
                resource_template=basic_resource_template)

        assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=None)
    async def test_save_and_deploy_resource_sends_resource_request_message(self, send_resource_request_mock, resource_template_repo, resource_repo, operations_repo, basic_resource_template):
        resource = sample_resource()
        operation = sample_resource_operation(resource_id=resource.id, operation_id=str(uuid.uuid4()))

        resource_repo.save_item = MagicMock(return_value=None)
        operations_repo.create_operations_item = MagicMock(return_value=operation)

        user = create_test_user()
        await save_and_deploy_resource(
            resource=resource,
            resource_repo=resource_repo,
            operations_repo=operations_repo,
            resource_template_repo=resource_template_repo,
            user=create_test_user(),
            resource_template=basic_resource_template)

        send_resource_request_mock.assert_called_once_with(
            resource=resource,
            operations_repo=operations_repo,
            resource_repo=resource_repo,
            user=user,
            resource_template_repo=resource_template_repo,
            resource_template=basic_resource_template,
            action=RequestAction.Install)

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @patch("api.routes.resource_helpers.send_resource_request_message", side_effect=Exception)
    async def test_save_and_deploy_resource_raises_503_if_send_request_fails(self, _, resource_template_repo, resource_repo, operations_repo, basic_resource_template):
        resource = sample_resource()
        resource_repo.save_item = MagicMock(return_value=None)
        resource_repo.delete_item = MagicMock(return_value=None)

        with pytest.raises(HTTPException) as ex:
            await save_and_deploy_resource(
                resource=resource,
                resource_repo=resource_repo,
                operations_repo=operations_repo,
                resource_template_repo=resource_template_repo,
                user=create_test_user(),
                resource_template=basic_resource_template)

        assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @patch("api.routes.resource_helpers.send_resource_request_message", side_effect=Exception)
    async def test_save_and_deploy_resource_deletes_item_from_db_if_send_request_fails(self, _, resource_template_repo, resource_repo, operations_repo, basic_resource_template):
        resource = sample_resource()

        resource_repo.save_item = MagicMock(return_value=None)
        resource_repo.delete_item = MagicMock(return_value=None)
        operations_repo.create_operation_item = MagicMock(return_value=None)

        with pytest.raises(HTTPException):
            await save_and_deploy_resource(
                resource=resource,
                resource_repo=resource_repo,
                operations_repo=operations_repo,
                resource_template_repo=resource_template_repo,
                user=create_test_user(),
                resource_template=basic_resource_template)

        resource_repo.delete_item.assert_called_once_with(resource.id)

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=None)
    @patch("api.routes.workspaces.OperationRepository")
    async def test_send_uninstall_message_sends_uninstall_message(self, operations_repo, send_request_mock, resource_template_repo, resource_repo, basic_resource_template):
        resource = sample_resource()
        user = create_test_user()

        await send_uninstall_message(
            resource=resource,
            resource_repo=resource_repo,
            operations_repo=operations_repo,
            resource_type=ResourceType.Workspace,
            resource_template_repo=resource_template_repo,
            user=user,
            resource_template=basic_resource_template)

        send_request_mock.assert_called_once_with(
            resource=resource,
            operations_repo=operations_repo,
            resource_repo=resource_repo,
            user=user,
            resource_template_repo=resource_template_repo,
            resource_template=basic_resource_template,
            action=RequestAction.UnInstall)

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @patch("api.routes.resource_helpers.send_resource_request_message", side_effect=Exception)
    @patch("api.routes.workspaces.OperationRepository")
    async def test_send_uninstall_message_raises_503_on_service_bus_exception(self, operations_repo, _, resource_template_repo, resource_repo, basic_resource_template):
        with pytest.raises(HTTPException) as ex:
            await send_uninstall_message(
                resource=sample_resource(),
                resource_repo=resource_repo,
                operations_repo=operations_repo,
                resource_type=ResourceType.Workspace,
                resource_template_repo=resource_template_repo,
                user=create_test_user(),
                resource_template=basic_resource_template)

        assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
