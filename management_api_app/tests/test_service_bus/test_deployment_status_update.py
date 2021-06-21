import json
import pytest
import uuid

from azure.servicebus import ServiceBusMessage
from mock import AsyncMock, patch

from db.errors import EntityDoesNotExist
from models.domain.resource import Status
from models.domain.workspace import Workspace
from models.domain.resource import Deployment
from resources import strings
from service_bus.deployment_status_update import receive_message_and_update_deployment

pytestmark = pytest.mark.asyncio

invalid_service_bus_message = ServiceBusMessage(body='{\'bad\': \'bad\'}', correlation_id="123")

valid_service_bus_message_body = {
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Deployed,
    "message": "test message"
}

valid_service_bus_message = ServiceBusMessage(body=json.dumps(valid_service_bus_message_body), correlation_id="456")


def create_sample_workspace_object(workspace_id):
    return Workspace(
        id=workspace_id,
        description="My workspace",
        resourceTemplateName="tre-workspace-vanilla",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.NotDeployed, message="")
    )


@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_receiving_bad_json_logs_error(app, sb_client, logging_mock):
    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[invalid_service_bus_message])
    sb_client().get_queue_receiver().complete_message = AsyncMock()

    await receive_message_and_update_deployment(app)

    logging_mock.assert_called_once_with(strings.DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT)
    sb_client().get_queue_receiver().complete_message.assert_called_once_with(invalid_service_bus_message)


@patch('service_bus.deployment_status_update.WorkspaceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_receiving_good_message(app, sb_client, logging_mock, repo):
    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[valid_service_bus_message])
    sb_client().get_queue_receiver().complete_message = AsyncMock()
    expected_workspace = create_sample_workspace_object(valid_service_bus_message_body["id"])
    repo().get_workspace_by_workspace_id.return_value = expected_workspace

    await receive_message_and_update_deployment(app)
    repo().get_workspace_by_workspace_id.assert_called_once_with(uuid.UUID(valid_service_bus_message_body["id"]))
    repo().update_workspace.assert_called_once_with(expected_workspace)
    logging_mock.assert_not_called()
    sb_client().get_queue_receiver().complete_message.assert_called_once_with(valid_service_bus_message)


@patch('service_bus.deployment_status_update.WorkspaceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_when_updating_non_existent_workspace_error_is_logged(app, sb_client, logging_mock, repo):
    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[valid_service_bus_message])
    sb_client().get_queue_receiver().complete_message = AsyncMock()
    repo().get_workspace_by_workspace_id.side_effect = EntityDoesNotExist

    await receive_message_and_update_deployment(app)
    expected_error_message = strings.DEPLOYMENT_STATUS_ID_NOT_FOUND.format(valid_service_bus_message_body["id"])
    logging_mock.assert_called_once_with(expected_error_message)
    sb_client().get_queue_receiver().complete_message.assert_called_once_with(valid_service_bus_message)


@patch('service_bus.deployment_status_update.WorkspaceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_when_updating_and_state_store_exception(app, sb_client, logging_mock, repo):
    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[valid_service_bus_message])
    sb_client().get_queue_receiver().complete_message = AsyncMock()
    repo().get_workspace_by_workspace_id.side_effect = Exception

    await receive_message_and_update_deployment(app)
    logging_mock.assert_called_once_with(strings.STATE_STORE_ENDPOINT_NOT_RESPONDING + " ")
    sb_client().get_queue_receiver().complete_message.assert_not_called()
