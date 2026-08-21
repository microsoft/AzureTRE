import asyncio
import copy
import json
from unittest.mock import MagicMock, ANY
from pydantic import TypeAdapter
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
    resource_repo.return_value.get_resource_dict_by_id.return_value = expected_workspace.model_dump()

    operation = create_sample_operation(test_sb_message["id"], RequestAction.Install)
    operation_repo.return_value.get_operation_by_id.return_value = operation

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(ServiceBusReceivedMessageMock(test_sb_message))

    assert complete_message is True
    resource_repo.return_value.get_resource_dict_by_id.assert_called_once_with(uuid.UUID(test_sb_message["id"]))
    resource_repo.return_value.update_item_dict.assert_called_once_with(expected_workspace.model_dump())
    logging_mock.assert_not_called()


@patch('service_bus.deployment_status_updater.tracer')
@patch('service_bus.deployment_status_updater.ResourceHistoryRepository.create')
@patch('service_bus.deployment_status_updater.ResourceTemplateRepository.create')
@patch('service_bus.deployment_status_updater.OperationRepository.create')
@patch('service_bus.deployment_status_updater.ResourceRepository.create')
async def test_process_message_sets_span_attributes(resource_repo, operation_repo, _, __, tracer_mock):
    expected_workspace = create_sample_workspace_object(test_sb_message["id"])
    resource_repo.return_value.get_resource_dict_by_id.return_value = expected_workspace.model_dump()

    operation = create_sample_operation(test_sb_message["id"], RequestAction.Install)
    operation_repo.return_value.get_operation_by_id.return_value = operation

    mock_span = MagicMock()
    tracer_mock.start_as_current_span.return_value.__enter__.return_value = mock_span

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    await status_updater.process_message(ServiceBusReceivedMessageMock(test_sb_message))

    mock_span.set_attribute.assert_any_call("step_id", test_sb_message["stepId"])
    mock_span.set_attribute.assert_any_call("operation_id", test_sb_message["operationId"])
    mock_span.set_attribute.assert_any_call("status", test_sb_message["status"])


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
    resource_repo.return_value.get_resource_dict_by_id.return_value = workspace.model_dump()

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
    resource_repo.return_value.get_resource_dict_by_id.return_value = resource.model_dump()

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
    resource_repo.return_value.update_item_dict.assert_called_once_with(expected_resource.model_dump())


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
    resource_repo.return_value.get_resource_dict_by_id.return_value = resource.model_dump()

    operation = create_sample_operation(resource.id, RequestAction.UnInstall)
    operations_repo.return_value.get_operation_by_id.return_value = operation

    expected_resource = resource

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    resource_repo.return_value.update_item_dict.assert_called_once_with(expected_resource.model_dump())


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
    resource_repo.return_value.get_resource_dict_by_id.return_value = basic_shared_service.model_dump()

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
    resource_repo.return_value.get_resource_dict_by_id.return_value = user_resource_multi.model_dump()

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
    deployment_status_update_message = TypeAdapter(DeploymentStatusUpdateMessage).validate_python(test_sb_message_with_outputs)

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


@patch('service_bus.deployment_status_updater.send_deployment_message')
@patch('service_bus.deployment_status_updater.WorkspaceRepository.create')
@patch('service_bus.deployment_status_updater.ResourceHistoryRepository.create')
@patch('service_bus.deployment_status_updater.ResourceTemplateRepository.create')
@patch("service_bus.deployment_status_updater.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
@patch('service_bus.deployment_status_updater.OperationRepository.create')
@patch('service_bus.deployment_status_updater.ResourceRepository.create')
async def test_workspace_service_uninstall_frees_address_space(
    resource_repo,
    operations_repo_mock,
    _,
    __,
    ___,
    workspace_repo_mock,
    send_deployment_message_mock
):
    workspace_service_id = "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76"
    parent_workspace_id = "1111c8e7-5c42-4fcb-a7fd-294cfc27aa76"
    address_space = "10.1.0.0/22"

    message_dict = {
        "operationId": OPERATION_ID,
        "stepId": "random-uuid",
        "id": workspace_service_id,
        "status": Status.Deleted,
        "message": "uninstall succeeded",
        "correlation_id": "test_correlation_id"
    }
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(message_dict)

    # Mock the operation showing RequestAction.UnInstall
    operation = create_sample_operation(workspace_service_id, RequestAction.UnInstall)
    operations_repo_mock.return_value.get_operation_by_id.return_value = operation

    # Mock WorkspaceService resource returned by get_resource_by_id
    workspace_service_mock = MagicMock()
    workspace_service_mock.deploymentStatus = None
    resource_repo.return_value.get_resource_by_id.return_value = workspace_service_mock

    # Mock resource dict representation returned by get_resource_dict_by_id
    workspace_service_dict = {
        "id": workspace_service_id,
        "resourceType": ResourceType.WorkspaceService.value,
        "workspaceId": parent_workspace_id,
        "properties": {
            "address_space": address_space
        }
    }
    resource_repo.return_value.get_resource_dict_by_id.return_value = workspace_service_dict

    # Mock parent workspace containing the address space to free
    parent_workspace = create_sample_workspace_object(parent_workspace_id)
    parent_workspace.properties = {"address_spaces": ["10.0.0.0/22", address_space]}
    parent_workspace.etag = "parent-workspace-etag"

    workspace_repo = AsyncMock()
    workspace_repo.get_workspace_by_id.return_value = parent_workspace
    workspace_repo_mock.return_value = workspace_repo

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    send_deployment_message_mock.assert_called_once()
    workspace_repo.patch_workspace.assert_not_called()
    await status_updater._free_workspace_address_space(operation)
    workspace_repo.patch_workspace.assert_called_once()
    called_args = workspace_repo.patch_workspace.call_args[0]
    assert called_args[0] == parent_workspace
    assert called_args[1].properties == {"address_spaces": ["10.0.0.0/22"]}
    assert called_args[2] == "parent-workspace-etag"


async def test_workspace_service_uninstall_frees_address_space_from_root_main_step():
    workspace_service_id = "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76"
    child_resource_id = "69b5c8e7-5c42-4fcb-a7fd-294cfc27aa76"
    parent_workspace_id = "1111c8e7-5c42-4fcb-a7fd-294cfc27aa76"
    address_space = "10.1.0.0/22"

    operation = create_sample_operation(workspace_service_id, RequestAction.UnInstall)
    operation.steps.insert(0, OperationStep(
        id="child-main",
        templateStepId="main",
        resourceId=child_resource_id,
        resourceType=ResourceType.UserResource,
        resourceAction=RequestAction.UnInstall
    ))

    status_updater = DeploymentStatusUpdater()
    status_updater.resource_repo = AsyncMock()
    status_updater.workspace_repo = AsyncMock()
    status_updater.resource_template_repo = AsyncMock()
    status_updater.resource_history_repo = AsyncMock()
    status_updater.resource_repo.get_resource_dict_by_id.return_value = {
        "id": workspace_service_id,
        "resourceType": ResourceType.WorkspaceService,
        "workspaceId": parent_workspace_id,
        "properties": {"address_space": address_space}
    }
    parent_workspace = create_sample_workspace_object(parent_workspace_id)
    parent_workspace.properties = {"address_spaces": [address_space]}
    parent_workspace.etag = "parent-workspace-etag"
    status_updater.workspace_repo.get_workspace_by_id.return_value = parent_workspace

    assert await status_updater._free_workspace_address_space(operation) is True
    status_updater.resource_repo.get_resource_dict_by_id.assert_awaited_once_with(workspace_service_id)
    status_updater.workspace_repo.patch_workspace.assert_awaited_once()


@pytest.mark.parametrize("missing_property", ["address_space", "workspaceId"])
@patch('service_bus.deployment_status_updater.WorkspaceRepository.create')
@patch('service_bus.deployment_status_updater.ResourceHistoryRepository.create')
@patch('service_bus.deployment_status_updater.ResourceTemplateRepository.create')
@patch("service_bus.deployment_status_updater.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
@patch('service_bus.deployment_status_updater.OperationRepository.create')
@patch('service_bus.deployment_status_updater.ResourceRepository.create')
async def test_workspace_service_uninstall_does_not_free_address_space_if_missing(
    resource_repo,
    operations_repo_mock,
    _,
    __,
    ___,
    workspace_repo_mock,
    missing_property
):
    workspace_service_id = "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76"
    parent_workspace_id = "1111c8e7-5c42-4fcb-a7fd-294cfc27aa76"
    address_space = "10.1.0.0/22"

    message_dict = {
        "operationId": OPERATION_ID,
        "stepId": "random-uuid",
        "id": workspace_service_id,
        "status": Status.Deleted,
        "message": "uninstall succeeded",
        "correlation_id": "test_correlation_id"
    }
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(message_dict)

    operation = create_sample_operation(workspace_service_id, RequestAction.UnInstall)
    operations_repo_mock.return_value.get_operation_by_id.return_value = operation

    workspace_service_mock = MagicMock()
    workspace_service_mock.deploymentStatus = None
    resource_repo.return_value.get_resource_by_id.return_value = workspace_service_mock

    workspace_service_dict = {
        "id": workspace_service_id,
        "resourceType": ResourceType.WorkspaceService,
        "workspaceId": parent_workspace_id,
        "properties": {
            "address_space": address_space
        }
    }
    if missing_property == "address_space":
        del workspace_service_dict["properties"]["address_space"]
    elif missing_property == "workspaceId":
        del workspace_service_dict["workspaceId"]

    resource_repo.return_value.get_resource_dict_by_id.return_value = workspace_service_dict

    workspace_repo = AsyncMock()
    workspace_repo_mock.return_value = workspace_repo

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    workspace_repo.patch_workspace.assert_not_called()


@patch('service_bus.deployment_status_updater.send_deployment_message')
@patch('service_bus.deployment_status_updater.WorkspaceRepository.create')
@patch('service_bus.deployment_status_updater.ResourceHistoryRepository.create')
@patch('service_bus.deployment_status_updater.ResourceTemplateRepository.create')
@patch("service_bus.deployment_status_updater.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
@patch('service_bus.deployment_status_updater.OperationRepository.create')
@patch('service_bus.deployment_status_updater.ResourceRepository.create')
async def test_workspace_service_uninstall_frees_address_space_with_retry_on_etag_conflict(
    resource_repo,
    operations_repo_mock,
    _,
    __,
    ___,
    workspace_repo_mock,
    send_deployment_message_mock
):
    from azure.cosmos.exceptions import CosmosAccessConditionFailedError

    workspace_service_id = "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76"
    parent_workspace_id = "1111c8e7-5c42-4fcb-a7fd-294cfc27aa76"
    address_space = "10.1.0.0/22"

    message_dict = {
        "operationId": OPERATION_ID,
        "stepId": "random-uuid",
        "id": workspace_service_id,
        "status": Status.Deleted,
        "message": "uninstall succeeded",
        "correlation_id": "test_correlation_id"
    }
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(message_dict)

    # Mock the operation showing RequestAction.UnInstall
    operation = create_sample_operation(workspace_service_id, RequestAction.UnInstall)
    operations_repo_mock.return_value.get_operation_by_id.return_value = operation

    # Mock WorkspaceService resource returned by get_resource_by_id
    workspace_service_mock = MagicMock()
    workspace_service_mock.deploymentStatus = None
    resource_repo.return_value.get_resource_by_id.return_value = workspace_service_mock

    # Mock resource dict representation returned by get_resource_dict_by_id
    workspace_service_dict = {
        "id": workspace_service_id,
        "resourceType": ResourceType.WorkspaceService,
        "workspaceId": parent_workspace_id,
        "properties": {
            "address_space": address_space
        }
    }
    resource_repo.return_value.get_resource_dict_by_id.return_value = workspace_service_dict

    # Mock parent workspace containing the address space to free
    parent_workspace = create_sample_workspace_object(parent_workspace_id)
    parent_workspace.properties = {"address_spaces": ["10.0.0.0/22", address_space]}
    parent_workspace.etag = "parent-workspace-etag"

    workspace_repo = AsyncMock()
    workspace_repo.get_workspace_by_id.return_value = parent_workspace

    # First attempt raises CosmosAccessConditionFailedError, second succeeds
    workspace_repo.patch_workspace.side_effect = [CosmosAccessConditionFailedError(), None]
    workspace_repo_mock.return_value = workspace_repo

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    send_deployment_message_mock.assert_called_once()
    await status_updater._free_workspace_address_space(operation)
    # One read prepares the synthetic upgrade, then two reads cover the retry.
    assert workspace_repo.get_workspace_by_id.call_count == 3
    # Assert patch_workspace called twice
    assert workspace_repo.patch_workspace.call_count == 2


@patch('service_bus.deployment_status_updater.send_deployment_message')
@patch('service_bus.deployment_status_updater.WorkspaceRepository.create')
@patch('service_bus.deployment_status_updater.ResourceHistoryRepository.create')
@patch('service_bus.deployment_status_updater.ResourceTemplateRepository.create')
@patch("service_bus.deployment_status_updater.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
@patch('service_bus.deployment_status_updater.OperationRepository.create')
@patch('service_bus.deployment_status_updater.ResourceRepository.create')
@patch('service_bus.deployment_status_updater.logger')
async def test_workspace_service_uninstall_logs_error_after_max_retries(
    logging_mock,
    resource_repo,
    operations_repo_mock,
    _,
    __,
    ___,
    workspace_repo_mock,
    send_deployment_message_mock
):
    from azure.cosmos.exceptions import CosmosAccessConditionFailedError

    workspace_service_id = "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76"
    parent_workspace_id = "1111c8e7-5c42-4fcb-a7fd-294cfc27aa76"
    address_space = "10.1.0.0/22"

    message_dict = {
        "operationId": OPERATION_ID,
        "stepId": "random-uuid",
        "id": workspace_service_id,
        "status": Status.Deleted,
        "message": "uninstall succeeded",
        "correlation_id": "test_correlation_id"
    }
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(message_dict)

    # Mock the operation showing RequestAction.UnInstall
    operation = create_sample_operation(workspace_service_id, RequestAction.UnInstall)
    operations_repo_mock.return_value.get_operation_by_id.return_value = operation

    # Mock WorkspaceService resource returned by get_resource_by_id
    workspace_service_mock = MagicMock()
    workspace_service_mock.deploymentStatus = None
    resource_repo.return_value.get_resource_by_id.return_value = workspace_service_mock

    # Mock resource dict representation returned by get_resource_dict_by_id
    workspace_service_dict = {
        "id": workspace_service_id,
        "resourceType": ResourceType.WorkspaceService,
        "workspaceId": parent_workspace_id,
        "properties": {
            "address_space": address_space
        }
    }
    resource_repo.return_value.get_resource_dict_by_id.return_value = workspace_service_dict

    # Mock parent workspace containing the address space to free
    parent_workspace = create_sample_workspace_object(parent_workspace_id)
    parent_workspace.properties = {"address_spaces": ["10.0.0.0/22", address_space]}
    parent_workspace.etag = "parent-workspace-etag"

    workspace_repo = AsyncMock()
    workspace_repo.get_workspace_by_id.return_value = parent_workspace

    # All attempts raise CosmosAccessConditionFailedError
    workspace_repo.patch_workspace.side_effect = CosmosAccessConditionFailedError()
    workspace_repo_mock.return_value = workspace_repo

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(service_bus_received_message_mock)

    # The uninstall message is complete; cleanup is deferred to the upgrade step.
    assert complete_message is True
    send_deployment_message_mock.assert_called_once()
    workspace_repo.patch_workspace.side_effect = CosmosAccessConditionFailedError()
    complete_message = await status_updater._free_workspace_address_space(operation)
    assert complete_message is False
    # Assert get_workspace_by_id and patch_workspace called max_retries = 3 times
    assert workspace_repo.get_workspace_by_id.call_count == 4
    assert workspace_repo.patch_workspace.call_count == 3
    # Assert we logged the final failure using the module's logger
    logging_mock.error.assert_called_once()
    assert "[ADDRESS_SPACE_CLEANUP_FAILED]" in logging_mock.error.call_args[0][0]


@patch('service_bus.deployment_status_updater.send_deployment_message')
@patch('service_bus.deployment_status_updater.update_resource_for_step')
@patch('service_bus.deployment_status_updater.WorkspaceRepository.create')
@patch('service_bus.deployment_status_updater.ResourceHistoryRepository.create')
@patch('service_bus.deployment_status_updater.ResourceTemplateRepository.create')
@patch("service_bus.deployment_status_updater.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
@patch('service_bus.deployment_status_updater.OperationRepository.create')
@patch('service_bus.deployment_status_updater.ResourceRepository.create')
async def test_workspace_service_uninstall_frees_address_space_before_enqueuing_next_step(
    resource_repo,
    operations_repo_mock,
    _,
    __,
    ___,
    workspace_repo_mock,
    update_resource_for_step_mock,
    send_deployment_message_mock
):
    workspace_service_id = "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76"
    parent_workspace_id = "1111c8e7-5c42-4fcb-a7fd-294cfc27aa76"
    address_space = "10.1.0.0/22"

    call_order = []

    # Create a 2-step uninstall operation (step 1: main, step 2: workspace upgrade)
    step1 = OperationStep(
        id="step-1",
        stepTitle="Uninstall workspace service",
        resourceId=workspace_service_id,
        resourceType=ResourceType.WorkspaceService,
        resourceAction=RequestAction.UnInstall,
        templateStepId="main",
        status=Status.Deleting
    )
    step2 = OperationStep(
        id="step-2",
        stepTitle="Upgrade workspace",
        resourceId=parent_workspace_id,
        resourceType=ResourceType.Workspace,
        resourceAction=RequestAction.Upgrade,
        templateStepId="workspace-upgrade",
        sourceTemplateResourceId=parent_workspace_id,
        status=Status.AwaitingUpdate
    )
    operation = Operation(
        id=OPERATION_ID,
        resourceId=workspace_service_id,
        resourcePath=f'/workspaces/{parent_workspace_id}/workspace-services/{workspace_service_id}',
        resourceVersion=0,
        action=RequestAction.UnInstall,
        steps=[step1, step2]
    )
    operations_repo_mock.return_value.get_operation_by_id.return_value = operation

    message_dict = {
        "operationId": OPERATION_ID,
        "stepId": "step-1",
        "id": workspace_service_id,
        "status": Status.Deleted,
        "message": "uninstall succeeded",
        "correlation_id": "test_correlation_id"
    }
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(message_dict)

    workspace_service_mock = MagicMock()
    workspace_service_mock.deploymentStatus = None
    resource_repo.return_value.get_resource_by_id.return_value = workspace_service_mock

    workspace_service_dict = {
        "id": workspace_service_id,
        "resourceType": ResourceType.WorkspaceService,
        "workspaceId": parent_workspace_id,
        "properties": {
            "address_space": address_space
        }
    }
    resource_repo.return_value.get_resource_dict_by_id.return_value = workspace_service_dict

    parent_workspace = create_sample_workspace_object(parent_workspace_id)
    parent_workspace.properties = {"address_spaces": ["10.0.0.0/22", address_space]}
    parent_workspace.etag = "parent-workspace-etag"

    workspace_repo = AsyncMock()
    workspace_repo.get_workspace_by_id.return_value = parent_workspace

    async def mock_patch_workspace(*args, **kwargs):
        call_order.append("patch_workspace")
        return parent_workspace, MagicMock()

    workspace_repo.patch_workspace = AsyncMock(side_effect=mock_patch_workspace)
    workspace_repo_mock.return_value = workspace_repo

    resource_to_send_mock = MagicMock()
    resource_to_send_mock.id = parent_workspace_id
    resource_to_send_mock.get_resource_request_message_payload.return_value = {}
    update_resource_for_step_mock.return_value = resource_to_send_mock

    async def mock_send_deployment_message(*args, **kwargs):
        call_order.append("send_deployment_message")

    send_deployment_message_mock.side_effect = mock_send_deployment_message

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(service_bus_received_message_mock)

    assert complete_message is True

    # The address remains reserved while the workspace upgrade is queued.
    assert call_order == ["send_deployment_message"]

    upgrade_message = ServiceBusReceivedMessageMock({
        "operationId": OPERATION_ID,
        "stepId": "step-2",
        "id": parent_workspace_id,
        "status": Status.Updated,
        "message": "workspace upgrade succeeded",
        "correlation_id": "test_correlation_id"
    })
    complete_message = await status_updater.process_message(upgrade_message)

    assert complete_message is True
    assert call_order == ["send_deployment_message", "patch_workspace"]


@patch("service_bus.deployment_status_updater.config")
@patch("service_bus.deployment_status_updater.credentials")
@patch("service_bus.deployment_status_updater.logger")
async def test_receive_messages_handles_credential_context_failure(logger_mock, credentials_mock, config_mock):
    config_mock.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE = "test_namespace"
    config_mock.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE = "test_queue"
    config_mock.SERVICE_BUS_MAX_WAIT_TIME = 10

    # Simulate exception when entering credential context manager
    credentials_mock.get_credential_async_context.side_effect = Exception("Credential error")

    status_updater = DeploymentStatusUpdater()

    # Run receive_messages in a task and cancel after one loop iteration
    task = asyncio.create_task(status_updater.receive_messages())
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    logger_mock.exception.assert_called_with("Unexpected error in deployment status receiver loop")
