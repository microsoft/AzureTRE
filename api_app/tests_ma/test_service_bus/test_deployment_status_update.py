import json
import pytest
import uuid

from mock import AsyncMock, patch

from db.errors import EntityDoesNotExist
from models.domain.workspace import Workspace
from models.domain.operation import Operation, Status
from resources import strings
from service_bus.deployment_status_update import receive_message_and_update_deployment


pytestmark = pytest.mark.asyncio

test_data = [
    'bad',
    '{"good": "json", "bad": "message"}'
]

OPERATION_ID = "0000c8e7-5c42-4fcb-a7fd-294cfc27aa76"

test_sb_message = {
    "operationId": OPERATION_ID,
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Deployed,
    "message": "test message"
}

test_sb_message_with_outputs = {
    "operationId": OPERATION_ID,
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Deployed,
    "message": "test message",
    "outputs": [
        {"Name": "name1", "Value": "value1", "Type": "type1"},
        {"Name": "name2", "Value": "\"value2\"", "Type": "type2"}
    ]
}


class ServiceBusReceivedMessageMock:
    def __init__(self, message: dict):
        self.message = json.dumps(message)
        self.correlation_id = "test_correlation_id"

    def __str__(self):
        return self.message


def create_sample_workspace_object(workspace_id):
    return Workspace(
        id=workspace_id,
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag='',
        properties={},
        resourcePath="test"
    )


def create_sample_operation(resource_id):
    return Operation(
        id=OPERATION_ID,
        resourceId=resource_id,
        resourcePath=f'/workspaces/{resource_id}',
        resourceVersion=0,
        message="test"
    )


@pytest.mark.parametrize("payload", test_data)
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_receiving_bad_json_logs_error(app, sb_client, logging_mock, payload):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(payload)

    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()

    await receive_message_and_update_deployment(app)

    error_message = logging_mock.call_args.args[0]
    assert error_message.startswith(strings.DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT)
    sb_client().get_queue_receiver().complete_message.assert_called_once_with(service_bus_received_message_mock)


@patch('service_bus.deployment_status_update.OperationRepository')
@patch('service_bus.deployment_status_update.ResourceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_receiving_good_message(app, sb_client, logging_mock, repo, _):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(test_sb_message)

    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()
    expected_workspace = create_sample_workspace_object(test_sb_message["id"])
    repo().get_resource_dict_by_id.return_value = expected_workspace.dict()

    await receive_message_and_update_deployment(app)

    repo().get_resource_dict_by_id.assert_called_once_with(uuid.UUID(test_sb_message["id"]))
    repo().update_item_dict.assert_called_once_with(expected_workspace.dict())
    logging_mock.assert_not_called()
    sb_client().get_queue_receiver().complete_message.assert_called_once_with(service_bus_received_message_mock)


@patch('service_bus.deployment_status_update.OperationRepository')
@patch('service_bus.deployment_status_update.ResourceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_when_updating_non_existent_workspace_error_is_logged(app, sb_client, logging_mock, repo, _):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(test_sb_message)

    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()
    repo().get_resource_dict_by_id.side_effect = EntityDoesNotExist

    await receive_message_and_update_deployment(app)

    expected_error_message = strings.DEPLOYMENT_STATUS_ID_NOT_FOUND.format(test_sb_message["id"])
    logging_mock.assert_called_once_with(expected_error_message)
    sb_client().get_queue_receiver().complete_message.assert_called_once_with(service_bus_received_message_mock)


@patch('service_bus.deployment_status_update.OperationRepository')
@patch('service_bus.deployment_status_update.ResourceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_when_updating_and_state_store_exception(app, sb_client, logging_mock, repo, _):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(test_sb_message)

    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()
    repo().get_resource_dict_by_id.side_effect = Exception

    await receive_message_and_update_deployment(app)

    logging_mock.assert_called_once_with(strings.STATE_STORE_ENDPOINT_NOT_RESPONDING + " ")
    sb_client().get_queue_receiver().complete_message.assert_not_called()


@patch('service_bus.deployment_status_update.OperationRepository')
@patch('service_bus.deployment_status_update.ResourceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_state_transitions_from_deployed_to_deploying_does_not_transition(app, sb_client, logging_mock, repo, _):
    updated_message = test_sb_message
    updated_message["status"] = Status.Deploying
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(updated_message)

    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()

    expected_workspace = create_sample_workspace_object(test_sb_message["id"])
    repo().get_resource_dict_by_id.return_value = expected_workspace.dict()

    await receive_message_and_update_deployment(app)

    repo().update_item_dict.assert_called_once_with(expected_workspace.dict())


@patch('service_bus.deployment_status_update.OperationRepository')
@patch('service_bus.deployment_status_update.ResourceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_state_transitions_from_deployed_to_deleted(app, sb_client, logging_mock, repo, operations_repo_mock):
    updated_message = test_sb_message
    updated_message["status"] = Status.Deleted
    updated_message["message"] = "Has been deleted"
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(updated_message)

    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()

    workspace = create_sample_workspace_object(test_sb_message["id"])
    repo().get_resource_dict_by_id.return_value = workspace.dict()

    operation = create_sample_operation(workspace.id)
    operations_repo_mock().get_operation_by_id.return_value = operation

    expected_operation = create_sample_operation(workspace.id)
    expected_operation.status = Status.Deleted
    expected_operation.message = updated_message["message"]

    await receive_message_and_update_deployment(app)

    operations_repo_mock().update_operation_status.assert_called_once_with(expected_operation.id, expected_operation.status, expected_operation.message)


@patch('service_bus.deployment_status_update.OperationRepository')
@patch('service_bus.deployment_status_update.ResourceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_state_transitions_from_deployed_to_delete_failed(app, sb_client, logging_mock, repo, operations_repo_mock):
    updated_message = test_sb_message
    updated_message["status"] = Status.Deleting
    updated_message["message"] = "Is being deleted"
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(updated_message)

    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()

    workspace = create_sample_workspace_object(test_sb_message["id"])
    repo().get_resource_dict_by_id.return_value = workspace.dict()

    operation = create_sample_operation(workspace.id)
    operations_repo_mock().get_operation_by_id.return_value = operation

    expected_operation = create_sample_operation(workspace.id)
    expected_operation.status = Status.Deleting
    expected_operation.message = updated_message["message"]

    await receive_message_and_update_deployment(app)

    operations_repo_mock().update_operation_status.assert_called_once_with(expected_operation.id, expected_operation.status, expected_operation.message)


@patch('service_bus.deployment_status_update.OperationRepository')
@patch('service_bus.deployment_status_update.ResourceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_outputs_are_added_to_resource_item(app, sb_client, logging_mock, repo, _):
    received_message = test_sb_message_with_outputs
    received_message["status"] = Status.Deployed
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(received_message)

    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()

    resource = create_sample_workspace_object(received_message["id"])
    resource.properties = {"exitingName": "exitingValue"}
    repo().get_resource_dict_by_id.return_value = resource.dict()

    new_params = {"name1": "value1", "name2": "value2"}

    expected_resource = resource
    expected_resource.properties = {**resource.properties, **new_params}

    await receive_message_and_update_deployment(app)

    repo().update_item_dict.assert_called_once_with(expected_resource.dict())


@patch('service_bus.deployment_status_update.OperationRepository')
@patch('service_bus.deployment_status_update.ResourceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_properties_dont_change_with_no_outputs(app, sb_client, logging_mock, repo, _):
    received_message = test_sb_message
    received_message["status"] = Status.Deployed
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(received_message)

    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()

    resource = create_sample_workspace_object(received_message["id"])
    resource.properties = {"exitingName": "exitingValue"}
    repo().get_resource_dict_by_id.return_value = resource.dict()

    expected_resource = resource

    await receive_message_and_update_deployment(app)

    repo().update_item_dict.assert_called_once_with(expected_resource.dict())
