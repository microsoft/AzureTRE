import copy
import json
from unittest.mock import MagicMock, ANY
from pydantic import parse_obj_as
import pytest
import uuid

from mock import AsyncMock, patch
from tests_ma.test_api.test_routes.test_resource_helpers import FAKE_CREATE_TIMESTAMP, FAKE_UPDATE_TIMESTAMP
from models.domain.request_action import RequestAction
from models.domain.resource import ResourceType

from db.errors import EntityDoesNotExist
from models.domain.workspace import Workspace
from models.domain.operation import DeploymentStatusUpdateMessage, Operation, OperationStep, Status
from resources import strings
from service_bus.deployment_status_updater import DeploymentStatusUpdater


pytestmark = pytest.mark.asyncio

test_data = [
    'bad',
    '{"good": "json", "bad": "message"}'
]

OPERATION_ID = "0000c8e7-5c42-4fcb-a7fd-294cfc27aa76"

test_sb_message = {
    "operationId": OPERATION_ID,
    "stepId": "random-uuid",
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Deployed,
    "message": "test message",
    "correlation_id": "test_correlation_id"
}

test_sb_message_with_outputs = {
    "operationId": OPERATION_ID,
    "stepId": "random-uuid",
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Deployed,
    "message": "test message",
    "outputs": [
        {"Name": "string1", "Value": "value1", "Type": "string"},
        {"Name": "string2", "Value": "\"value2\"", "Type": "string"},
        {"Name": "boolean1", "Value": "True", "Type": "boolean"},
        {"Name": "boolean2", "Value": "true", "Type": "boolean"},
        {"Name": "boolean3", "Value": "\"true\"", "Type": "boolean"},
        {"Name": "list1", "Value": "['one', 'two']", "Type": "string"},
        {"Name": "list2", "Value": ['one', 'two'], "Type": "string"}
    ]
}

test_sb_message_multi_step_1_complete = {
    "operationId": OPERATION_ID,
    "stepId": "random-uuid-1",
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Updated,
    "message": "upgrade succeeded"
}

test_sb_message_multi_step_3_complete = {
    "operationId": OPERATION_ID,
    "stepId": "random-uuid-3",
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Updated,
    "message": "upgrade succeeded"
}


class ServiceBusReceivedMessageMock:
    def __init__(self, message: dict):
        self.message = json.dumps(message)
        self.correlation_id = "test_correlation_id"
        self.session_id = "test_session_id"

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
                id="random-uuid",
                templateStepId="main",
                resourceId=resource_id,
                stepTitle=f"main step for {resource_id}",
                resourceTemplateName="workspace-base",
                resourceType=ResourceType.Workspace,
                resourceAction=request_action,
                updatedWhen=FAKE_UPDATE_TIMESTAMP,
                sourceTemplateResourceId=resource_id
            )
        ]
    )


@pytest.mark.parametrize("payload", test_data)
@patch('services.logging.logger.exception')
async def test_receiving_bad_json_logs_error(logging_mock, payload):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(payload)

    status_updater = DeploymentStatusUpdater()
    complete_message = await status_updater.process_message(service_bus_received_message_mock)

    # bad message data will fail. we don't mark complete=true since we want the message in the DLQ
    assert complete_message is False

    # check we logged the error
    error_message = logging_mock.call_args.args[0]
    assert error_message.startswith(strings.DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT)


@patch('service_bus.deployment_status_updater.ResourceHistoryRepository.create')
@patch('service_bus.deployment_status_updater.ResourceTemplateRepository.create')
@patch('service_bus.deployment_status_updater.OperationRepository.create')
@patch('service_bus.deployment_status_updater.ResourceRepository.create')
@patch('services.logging.logger.exception')
async def test_receiving_good_message(logging_mock, resource_repo, operation_repo, _, __):
    expected_workspace = create_sample_workspace_object(test_sb_message["id"])
    resource_repo.return_value.get_resource_dict_by_id.return_value = expected_workspace.dict()

    operation = create_sample_operation(test_sb_message["id"], RequestAction.Install)
    operation_repo.return_value.get_operation_by_id.return_value = operation

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(ServiceBusReceivedMessageMock(test_sb_message))

    assert complete_message is True
    resource_repo.return_value.get_resource_dict_by_id.assert_called_once_with(uuid.UUID(test_sb_message["id"]))
    resource_repo.return_value.update_item_dict.assert_called_once_with(expected_workspace.dict())
    logging_mock.assert_not_called()


@patch('service_bus.deployment_status_updater.ResourceHistoryRepository.create')
@patch('service_bus.deployment_status_updater.ResourceTemplateRepository.create')
@patch('service_bus.deployment_status_updater.OperationRepository.create')
@patch('service_bus.deployment_status_updater.ResourceRepository.create')
@patch('services.logging.logger.exception')
async def test_when_updating_non_existent_workspace_error_is_logged(logging_mock, resource_repo, operation_repo, _, __):
    resource_repo.return_value.get_resource_dict_by_id.side_effect = EntityDoesNotExist

    operation = create_sample_operation(test_sb_message["id"], RequestAction.Install)
    operation_repo.return_value.get_operation_by_id.return_value = operation

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(ServiceBusReceivedMessageMock(test_sb_message))

    assert complete_message is True
    expected_error_message = strings.DEPLOYMENT_STATUS_ID_NOT_FOUND.format(test_sb_message["id"])
    logging_mock.assert_called_once_with(expected_error_message)


@patch('service_bus.deployment_status_updater.ResourceHistoryRepository.create')
@patch('service_bus.deployment_status_updater.ResourceTemplateRepository.create')
@patch('service_bus.deployment_status_updater.OperationRepository.create')
@patch('service_bus.deployment_status_updater.ResourceRepository.create')
@patch('services.logging.logger.exception')
async def test_when_updating_and_state_store_exception(logging_mock, resource_repo, operation_repo, _, __):
    resource_repo.return_value.get_resource_dict_by_id.side_effect = Exception

    operation = create_sample_operation(test_sb_message["id"], RequestAction.Install)
    operation_repo.return_value.get_operation_by_id.return_value = operation

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(ServiceBusReceivedMessageMock(test_sb_message))

    logging_mock.assert_called_once_with("Failed to update status")
    assert complete_message is False


@patch('service_bus.deployment_status_updater.ResourceHistoryRepository.create')
@patch('service_bus.deployment_status_updater.ResourceTemplateRepository.create')
@patch("service_bus.deployment_status_updater.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
@patch('service_bus.deployment_status_updater.OperationRepository.create')
@patch('service_bus.deployment_status_updater.ResourceRepository.create')
async def test_state_transitions_from_deployed_to_deleted(resource_repo, operations_repo_mock, _, __, ___):
    updated_message = test_sb_message
    updated_message["status"] = Status.Deleted
    updated_message["message"] = "Has been deleted"
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(updated_message)

    workspace = create_sample_workspace_object(test_sb_message["id"])
    resource_repo.return_value.get_resource_dict_by_id.return_value = workspace.dict()

    operation = create_sample_operation(workspace.id, RequestAction.UnInstall)
    operation.steps[0].status = Status.Deployed
    operations_repo_mock.return_value.get_operation_by_id.return_value = operation

    expected_operation = create_sample_operation(workspace.id, RequestAction.UnInstall)
    expected_operation.steps[0].status = Status.Deleted
    expected_operation.steps[0].message = updated_message["message"]
    expected_operation.status = Status.Deleted
    expected_operation.message = updated_message["message"]

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    operations_repo_mock.return_value.update_item.assert_called_once_with(expected_operation)


@patch('service_bus.deployment_status_updater.ResourceHistoryRepository.create')
@patch('service_bus.deployment_status_updater.ResourceTemplateRepository.create')
@patch('service_bus.deployment_status_updater.OperationRepository.create')
@patch('service_bus.deployment_status_updater.ResourceRepository.create')
async def test_outputs_are_added_to_resource_item(resource_repo, operations_repo, _, __):
    received_message = test_sb_message_with_outputs
    received_message["status"] = Status.Deployed
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(received_message)

    resource = create_sample_workspace_object(received_message["id"])
    resource.properties = {"exitingName": "exitingValue"}
    resource_repo.return_value.get_resource_dict_by_id.return_value = resource.dict()

    new_params = {
        "string1": "value1",
        "string2": "value2",
        "boolean1": True,
        "boolean2": True,
        "boolean3": True,
        "list1": "['one', 'two']",
        "list2": ["one", "two"],
    }

    expected_resource = resource
    expected_resource.properties = {**resource.properties, **new_params}

    operation = create_sample_operation(resource.id, RequestAction.UnInstall)
    operations_repo.return_value.get_operation_by_id.return_value = operation

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    resource_repo.return_value.update_item_dict.assert_called_once_with(expected_resource)


@patch('service_bus.deployment_status_updater.ResourceHistoryRepository.create')
@patch('service_bus.deployment_status_updater.ResourceTemplateRepository.create')
@patch('service_bus.deployment_status_updater.OperationRepository.create')
@patch('service_bus.deployment_status_updater.ResourceRepository.create')
async def test_properties_dont_change_with_no_outputs(resource_repo, operations_repo, _, __):
    received_message = test_sb_message
    received_message["status"] = Status.Deployed
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(received_message)

    resource = create_sample_workspace_object(received_message["id"])
    resource.properties = {"exitingName": "exitingValue"}
    resource_repo.return_value.get_resource_dict_by_id.return_value = resource.dict()

    operation = create_sample_operation(resource.id, RequestAction.UnInstall)
    operations_repo.return_value.get_operation_by_id.return_value = operation

    expected_resource = resource

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    resource_repo.return_value.update_item_dict.assert_called_once_with(expected_resource.dict())


@patch('service_bus.deployment_status_updater.ResourceHistoryRepository.create')
@patch('service_bus.deployment_status_updater.ResourceTemplateRepository.create')
@patch('service_bus.deployment_status_updater.update_resource_for_step')
@patch('service_bus.deployment_status_updater.OperationRepository.create')
@patch('service_bus.deployment_status_updater.ResourceRepository.create')
@patch('service_bus.helpers.ServiceBusClient')
async def test_multi_step_operation_sends_next_step(sb_sender_client, resource_repo, operations_repo, update_resource_for_step, _, __, multi_step_operation, user_resource_multi, basic_shared_service):
    received_message = test_sb_message_multi_step_1_complete
    received_message["status"] = Status.Updated
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(received_message)
    sb_sender_client().get_queue_sender().send_messages = AsyncMock()

    # step 1 resource
    resource_repo.return_value.get_resource_dict_by_id.return_value = basic_shared_service.dict()

    # step 2 resource
    resource_repo.return_value.get_resource_by_id.return_value = user_resource_multi

    operations_repo.return_value.update_item.return_value = MagicMock(return_value=basic_shared_service)

    # get the multi-step operation and process it
    operations_repo.return_value.get_operation_by_id.return_value = multi_step_operation
    update_resource_for_step.return_value = user_resource_multi

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(service_bus_received_message_mock)

    assert complete_message is True

    # check the resource is updated as expected
    update_resource_for_step.assert_called_once_with(
        operation_step=ANY,
        resource_repo=ANY,
        resource_template_repo=ANY,
        resource_history_repo=ANY,
        root_resource=ANY,
        step_resource=ANY,
        resource_to_update_id=multi_step_operation.steps[1].resourceId,
        primary_action=ANY,
        user=ANY)
    resource_repo.return_value.get_resource_by_id.assert_called_with(multi_step_operation.resourceId)

    # check the operation is updated as expected
    expected_operation = copy.deepcopy(multi_step_operation)
    expected_operation.status = Status.PipelineRunning
    expected_operation.message = "Multi step pipeline running. See steps for details."
    expected_operation.steps[0].status = Status.Updated
    expected_operation.steps[0].message = "upgrade succeeded"
    operations_repo.return_value.update_item.assert_called_once_with(expected_operation)

    # check it sent a message on for the next step
    sb_sender_client().get_queue_sender().send_messages.assert_called_once()


@patch('service_bus.deployment_status_updater.ResourceHistoryRepository.create')
@patch('service_bus.deployment_status_updater.ResourceTemplateRepository.create')
@patch('service_bus.deployment_status_updater.OperationRepository.create')
@patch('service_bus.deployment_status_updater.ResourceRepository.create')
@patch('service_bus.helpers.ServiceBusClient')
async def test_multi_step_operation_ends_at_last_step(sb_sender_client, resource_repo, operations_repo, _, __, multi_step_operation, user_resource_multi, basic_shared_service):
    received_message = test_sb_message_multi_step_3_complete
    received_message["status"] = Status.Updated
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(received_message)
    sb_sender_client().get_queue_sender().send_messages = AsyncMock()

    # step 2 resource
    resource_repo.return_value.get_resource_dict_by_id.return_value = user_resource_multi.dict()

    # step 3 resource
    resource_repo.return_value.get_resource_by_id.return_value = basic_shared_service

    operations_repo.return_value.update_item.return_value = MagicMock(return_value=user_resource_multi)

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

    operations_repo.return_value.get_operation_by_id.return_value = in_flight_op

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(service_bus_received_message_mock)
    assert complete_message is True

    # check the operation is updated as expected - both step and overall status
    expected_operation = copy.deepcopy(in_flight_op)
    expected_operation.status = Status.Deployed
    expected_operation.message = "Multi step pipeline completed successfully"
    expected_operation.steps[2].status = Status.Updated
    expected_operation.steps[2].message = "upgrade succeeded"
    operations_repo.return_value.update_item.assert_called_once_with(expected_operation)

    # check it did _not_ enqueue another message
    sb_sender_client().get_queue_sender().send_messages.assert_not_called()


async def test_convert_outputs_to_dict():
    # Test case 1: Empty list of outputs
    outputs_list = []
    expected_result = {}

    status_updater = DeploymentStatusUpdater()
    assert status_updater.convert_outputs_to_dict(outputs_list) == expected_result

    # Test case 2: List of outputs with mixed types
    deployment_status_update_message = parse_obj_as(DeploymentStatusUpdateMessage, test_sb_message_with_outputs)

    expected_result = {
        'string1': 'value1',
        'string2': 'value2',
        'boolean1': True,
        'boolean2': True,
        'boolean3': True,
        'list1': "['one', 'two']",
        'list2': ['one', 'two']
    }
    assert status_updater.convert_outputs_to_dict(deployment_status_update_message.outputs) == expected_result
