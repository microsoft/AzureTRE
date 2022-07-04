import copy
import json
from unittest.mock import MagicMock, ANY
import pytest
import uuid

from mock import AsyncMock, patch
from tests_ma.test_api.test_routes.test_resource_helpers import FAKE_CREATE_TIMESTAMP, FAKE_UPDATE_TIMESTAMP
from models.domain.request_action import RequestAction
from models.domain.resource import ResourceType

from db.errors import EntityDoesNotExist
from models.domain.workspace import Workspace
from models.domain.operation import Operation, OperationStep, Status
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
    "stepId": "main",
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Deployed,
    "message": "test message"
}

test_sb_message_with_outputs = {
    "operationId": OPERATION_ID,
    "stepId": "main",
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Deployed,
    "message": "test message",
    "outputs": [
        {"Name": "name1", "Value": "value1", "Type": "type1"},
        {"Name": "name2", "Value": "\"value2\"", "Type": "type2"}
    ]
}

test_sb_message_multi_step_1_complete = {
    "operationId": OPERATION_ID,
    "stepId": "pre-step-1",
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Updated,
    "message": "upgrade succeeded"
}

test_sb_message_multi_step_3_complete = {
    "operationId": OPERATION_ID,
    "stepId": "post-step-1",
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Updated,
    "message": "upgrade succeeded"
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


def create_sample_operation(resource_id, request_action):
    return Operation(
        id=OPERATION_ID,
        resourceId=resource_id,
        resourcePath=f'/workspaces/{resource_id}',
        resourceVersion=0,
        action=request_action,
        message="test",
        createdWhen=FAKE_CREATE_TIMESTAMP,
        updatedWhen=FAKE_UPDATE_TIMESTAMP,
        steps=[
            OperationStep(
                stepId="main",
                resourceId=resource_id,
                stepTitle=f"main step for {resource_id}",
                resourceTemplateName="workspace-base",
                resourceType=ResourceType.Workspace,
                resourceAction=request_action,
                updatedWhen=FAKE_UPDATE_TIMESTAMP
            )
        ]
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
async def test_receiving_good_message(app, sb_client, logging_mock, repo, operation_repo):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(test_sb_message)

    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()
    expected_workspace = create_sample_workspace_object(test_sb_message["id"])
    repo().get_resource_dict_by_id.return_value = expected_workspace.dict()

    operation = create_sample_operation(test_sb_message["id"], RequestAction.Install)
    operation_repo().get_operation_by_id.return_value = operation

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
async def test_when_updating_non_existent_workspace_error_is_logged(app, sb_client, logging_mock, repo, operation_repo):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(test_sb_message)

    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()
    repo().get_resource_dict_by_id.side_effect = EntityDoesNotExist

    operation = create_sample_operation(test_sb_message["id"], RequestAction.Install)
    operation_repo().get_operation_by_id.return_value = operation

    await receive_message_and_update_deployment(app)

    expected_error_message = strings.DEPLOYMENT_STATUS_ID_NOT_FOUND.format(test_sb_message["id"])
    logging_mock.assert_called_once_with(expected_error_message)
    sb_client().get_queue_receiver().complete_message.assert_called_once_with(service_bus_received_message_mock)


@patch('service_bus.deployment_status_update.OperationRepository')
@patch('service_bus.deployment_status_update.ResourceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_when_updating_and_state_store_exception(app, sb_client, logging_mock, repo, operation_repo):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(test_sb_message)

    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()
    repo().get_resource_dict_by_id.side_effect = Exception

    operation = create_sample_operation(test_sb_message["id"], RequestAction.Install)
    operation_repo().get_operation_by_id.return_value = operation

    await receive_message_and_update_deployment(app)

    logging_mock.assert_called_once_with(strings.STATE_STORE_ENDPOINT_NOT_RESPONDING + " ")
    sb_client().get_queue_receiver().complete_message.assert_not_called()


@patch("service_bus.deployment_status_update.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
@patch('service_bus.deployment_status_update.OperationRepository')
@patch('service_bus.deployment_status_update.ResourceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_state_transitions_from_deployed_to_deleted(app, sb_client, logging_mock, repo, operations_repo_mock, _):
    updated_message = test_sb_message
    updated_message["status"] = Status.Deleted
    updated_message["message"] = "Has been deleted"
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(updated_message)

    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()

    workspace = create_sample_workspace_object(test_sb_message["id"])
    repo().get_resource_dict_by_id.return_value = workspace.dict()

    operation = create_sample_operation(workspace.id, RequestAction.UnInstall)
    operation.steps[0].status = Status.Deployed
    operations_repo_mock().get_operation_by_id.return_value = operation

    expected_operation = create_sample_operation(workspace.id, RequestAction.UnInstall)
    expected_operation.steps[0].status = Status.Deleted
    expected_operation.steps[0].message = updated_message["message"]
    expected_operation.status = Status.Deleted
    expected_operation.message = updated_message["message"]

    await receive_message_and_update_deployment(app)

    operations_repo_mock().update_item.assert_called_once_with(expected_operation)


@patch('service_bus.deployment_status_update.OperationRepository')
@patch('service_bus.deployment_status_update.ResourceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_outputs_are_added_to_resource_item(app, sb_client, logging_mock, repo, operations_repo):
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

    operation = create_sample_operation(resource.id, RequestAction.UnInstall)
    operations_repo().get_operation_by_id.return_value = operation

    await receive_message_and_update_deployment(app)

    repo().update_item_dict.assert_called_once_with(expected_resource)


@patch('service_bus.deployment_status_update.OperationRepository')
@patch('service_bus.deployment_status_update.ResourceRepository')
@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_properties_dont_change_with_no_outputs(app, sb_client, logging_mock, repo, operations_repo):
    received_message = test_sb_message
    received_message["status"] = Status.Deployed
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(received_message)

    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()

    resource = create_sample_workspace_object(received_message["id"])
    resource.properties = {"exitingName": "exitingValue"}
    repo().get_resource_dict_by_id.return_value = resource.dict()

    operation = create_sample_operation(resource.id, RequestAction.UnInstall)
    operations_repo().get_operation_by_id.return_value = operation

    expected_resource = resource

    await receive_message_and_update_deployment(app)

    repo().update_item_dict.assert_called_once_with(expected_resource.dict())


@patch('service_bus.deployment_status_update.update_resource_for_step')
@patch('service_bus.deployment_status_update.OperationRepository')
@patch('service_bus.deployment_status_update.ResourceRepository')
@patch('service_bus.helpers.ServiceBusClient')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_multi_step_operation_sends_next_step(app, sb_client, sb_sender_client, repo, operations_repo, update_resource_for_step, multi_step_operation, user_resource_multi, basic_shared_service):
    received_message = test_sb_message_multi_step_1_complete
    received_message["status"] = Status.Updated
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(received_message)
    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()
    sb_sender_client().get_queue_sender().send_messages = AsyncMock()

    # step 1 resource
    repo().get_resource_dict_by_id.return_value = basic_shared_service.dict()

    # step 2 resource
    repo().get_resource_by_id.return_value = user_resource_multi

    operations_repo().update_item = MagicMock(return_value=basic_shared_service)

    # get the multi-step operation and process it
    operations_repo().get_operation_by_id.return_value = multi_step_operation
    update_resource_for_step.return_value = user_resource_multi

    await receive_message_and_update_deployment(app)

    # check the resource is updated as expected
    update_resource_for_step.assert_called_once_with(
        operation_step=ANY,
        resource_repo=ANY,
        resource_template_repo=ANY,
        primary_resource=user_resource_multi,
        resource_to_update_id=multi_step_operation.steps[1].resourceId,
        primary_action=ANY,
        user=ANY)
    repo().get_resource_by_id.assert_called_with(multi_step_operation.resourceId)

    # check the operation is updated as expected
    expected_operation = copy.deepcopy(multi_step_operation)
    expected_operation.status = Status.PipelineRunning
    expected_operation.message = "Multi step pipeline running. See steps for details."
    expected_operation.steps[0].status = Status.Updated
    expected_operation.steps[0].message = "upgrade succeeded"
    operations_repo().update_item.assert_called_once_with(expected_operation)

    # check it sent a message on for the next step
    sb_sender_client().get_queue_sender().send_messages.assert_called_once()


@patch('service_bus.deployment_status_update.OperationRepository')
@patch('service_bus.deployment_status_update.ResourceRepository')
@patch('service_bus.helpers.ServiceBusClient')
@patch('service_bus.deployment_status_update.ServiceBusClient')
@patch('fastapi.FastAPI')
async def test_multi_step_operation_ends_at_last_step(app, sb_client, sb_sender_client, repo, operations_repo, multi_step_operation, user_resource_multi, basic_shared_service):
    received_message = test_sb_message_multi_step_3_complete
    received_message["status"] = Status.Updated
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(received_message)
    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[service_bus_received_message_mock])
    sb_client().get_queue_receiver().complete_message = AsyncMock()
    sb_sender_client().get_queue_sender().send_messages = AsyncMock()

    # step 2 resource
    repo().get_resource_dict_by_id.return_value = user_resource_multi.dict()

    # step 3 resource
    repo().get_resource_by_id.return_value = basic_shared_service

    operations_repo().update_item = MagicMock(return_value=user_resource_multi)

    # get the multi-step operation and process it
    # simulate what the op would look like after step 2
    in_flight_op = copy.deepcopy(multi_step_operation)
    in_flight_op.status = Status.PipelineRunning
    in_flight_op.message = "Multi step pipeline running. See steps for details."
    in_flight_op.steps[0].status = Status.Updated
    in_flight_op.steps[0].message = "upgrade succeeded"
    in_flight_op.steps[1].status = Status.Deployed
    in_flight_op.steps[1].message = "install succeeded"
    in_flight_op.steps[2].status = Status.Updating

    operations_repo().get_operation_by_id.return_value = in_flight_op
    await receive_message_and_update_deployment(app)

    # check the operation is updated as expected - both step and overall status
    expected_operation = copy.deepcopy(in_flight_op)
    expected_operation.status = Status.Deployed
    expected_operation.message = "Multi step pipeline completed successfully"
    expected_operation.steps[2].status = Status.Updated
    expected_operation.steps[2].message = "upgrade succeeded"
    operations_repo().update_item.assert_called_once_with(expected_operation)

    # check it did _not_ enqueue another message
    sb_sender_client().get_queue_sender().send_messages.assert_not_called()
