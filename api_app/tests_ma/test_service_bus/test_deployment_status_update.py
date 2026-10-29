import copy
import json
from unittest.mock import AsyncMock, MagicMock, ANY, patch
from pydantic import TypeAdapter
import pytest
import uuid

from tests_ma.test_api.test_routes.test_resource_helpers import FAKE_CREATE_TIMESTAMP, FAKE_UPDATE_TIMESTAMP
from models.domain.request_action import RequestAction
from models.domain.resource import Output, ResourceType

from db.errors import EntityDoesNotExist
from models.domain.workspace import Workspace
from models.domain.workspace_service import WorkspaceService
from models.domain.operation import DeploymentStatusUpdateMessage, Operation, OperationStep, Status
from resources import strings
from service_bus.deployment_status_updater import DeploymentStatusUpdater
from tests_ma.test_service_bus.test_helpers import (
    StopReceiveMessages,
    credential_context,
    queue_receiver_context,
    service_bus_client_context,
)


pytestmark = pytest.mark.asyncio

test_data = ["bad", '{"good": "json", "bad": "message"}']

OPERATION_ID = "0000c8e7-5c42-4fcb-a7fd-294cfc27aa76"

test_sb_message = {
    "operationId": OPERATION_ID,
    "stepId": "random-uuid",
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Deployed,
    "message": "test message",
    "correlation_id": "test_correlation_id",
}

test_sb_message_with_outputs = {
    "operationId": OPERATION_ID,
    "stepId": "random-uuid",
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Deployed,
    "message": "test message",
    "outputs": [
        {"Name": "string1", "Value": "value1", "Type": "string"},
        {"Name": "string2", "Value": '"value2"', "Type": "string"},
        {"Name": "boolean1", "Value": "True", "Type": "boolean"},
        {"Name": "boolean2", "Value": "true", "Type": "boolean"},
        {"Name": "boolean3", "Value": '"true"', "Type": "boolean"},
        {"Name": "list1", "Value": "['one', 'two']", "Type": "string"},
        {"Name": "list2", "Value": ["one", "two"], "Type": "string"},
    ],
}

test_sb_message_multi_step_1_complete = {
    "operationId": OPERATION_ID,
    "stepId": "random-uuid-1",
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Updated,
    "message": "upgrade succeeded",
}

test_sb_message_multi_step_3_complete = {
    "operationId": OPERATION_ID,
    "stepId": "random-uuid-3",
    "id": "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
    "status": Status.Updated,
    "message": "upgrade succeeded",
}


class ServiceBusReceivedMessageMock:
    def __init__(self, message: dict):
        self.message = json.dumps(message)
        self.correlation_id = "test_correlation_id"
        self.session_id = "test_session_id"

    def __str__(self):
        return self.message


async def run_receive_messages_with_mocks(service_bus_client, time_values, client_side_effect=None):
    credential = credential_context()
    receiver = queue_receiver_context(session=True, iterate=True)
    service_bus_client.get_queue_receiver.return_value = receiver
    renewer = MagicMock()

    with (
        patch(
            "service_bus.deployment_status_updater.credentials.get_credential_async_context", return_value=credential
        ),
        patch(
            "service_bus.deployment_status_updater.ServiceBusClient",
            return_value=service_bus_client,
            side_effect=client_side_effect,
        ),
        patch("service_bus.deployment_status_updater.time.time", side_effect=time_values),
        patch("service_bus.deployment_status_updater.asyncio.sleep", new_callable=AsyncMock),
        patch("service_bus.deployment_status_updater.AutoLockRenewer") as auto_lock_renewer,
    ):
        auto_lock_renewer.return_value.__aenter__ = AsyncMock(return_value=renewer)
        auto_lock_renewer.return_value.__aexit__ = AsyncMock(return_value=False)
        await DeploymentStatusUpdater().receive_messages()


async def test_receive_messages_reuses_client_for_multiple_polls():
    service_bus_client = service_bus_client_context()
    time_call_count = 0
    client_call_count = 0

    def time_after_two_polls():
        nonlocal time_call_count
        time_call_count += 1
        return 0 if time_call_count <= 5 else 3601

    def create_client(*args, **kwargs):
        nonlocal client_call_count
        client_call_count += 1
        if client_call_count == 1:
            return service_bus_client
        raise StopReceiveMessages()

    with pytest.raises(StopReceiveMessages):
        await run_receive_messages_with_mocks(service_bus_client, time_after_two_polls, create_client)

    assert service_bus_client.get_queue_receiver.call_count == 2
    service_bus_client.__aenter__.assert_awaited_once()
    service_bus_client.__aexit__.assert_awaited_once()


async def test_receive_messages_closes_client_before_hourly_recreation():
    first_client = service_bus_client_context()

    def create_client(*args, **kwargs):
        if create_client.called:
            raise StopReceiveMessages()
        create_client.called = True
        return first_client

    create_client.called = False

    with pytest.raises(StopReceiveMessages):
        with (
            patch(
                "service_bus.deployment_status_updater.credentials.get_credential_async_context",
                return_value=credential_context(),
            ),
            patch("service_bus.deployment_status_updater.ServiceBusClient", side_effect=create_client),
            patch("service_bus.deployment_status_updater.time.time", side_effect=[0, 0, 0, 3601]),
            patch("service_bus.deployment_status_updater.asyncio.sleep", new_callable=AsyncMock),
        ):
            first_client.get_queue_receiver.return_value = queue_receiver_context()
            await DeploymentStatusUpdater().receive_messages()

    first_client.__aexit__.assert_awaited_once()
    assert first_client.get_queue_receiver.call_count == 1


async def test_receive_messages_closes_client_after_receiver_failure():
    service_bus_client = service_bus_client_context()
    service_bus_client.get_queue_receiver.side_effect = RuntimeError("receiver failed")
    client_call_count = 0

    def create_client(*args, **kwargs):
        nonlocal client_call_count
        client_call_count += 1
        if client_call_count == 1:
            return service_bus_client
        raise StopReceiveMessages()

    with pytest.raises(StopReceiveMessages):
        await run_receive_messages_with_mocks(service_bus_client, lambda: 0, create_client)

    service_bus_client.__aenter__.assert_awaited_once()
    service_bus_client.__aexit__.assert_awaited_once()


def create_sample_workspace_object(workspace_id):
    return Workspace(
        id=workspace_id,
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties={},
        resourcePath="test",
    )


def create_sample_operation(resource_id, request_action):
    return Operation(
        id=OPERATION_ID,
        resourceId=resource_id,
        resourcePath=f"/workspaces/{resource_id}",
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
                sourceTemplateResourceId=resource_id,
            )
        ],
    )


@pytest.mark.parametrize("payload", test_data)
@patch("services.logging.logger.exception")
async def test_receiving_bad_json_logs_error(logging_mock, payload):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(payload)

    status_updater = DeploymentStatusUpdater()
    complete_message = await status_updater.process_message(service_bus_received_message_mock)

    # bad message data will fail. we don't mark complete=true since we want the message in the DLQ
    assert complete_message is False

    # check we logged the error
    error_message = logging_mock.call_args.args[0]
    assert error_message.startswith(strings.DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT)


@patch("service_bus.deployment_status_updater.ResourceHistoryRepository.create")
@patch("service_bus.deployment_status_updater.ResourceTemplateRepository.create")
@patch("service_bus.deployment_status_updater.OperationRepository.create")
@patch("service_bus.deployment_status_updater.ResourceRepository.create")
@patch("services.logging.logger.exception")
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


@patch("service_bus.deployment_status_updater.ResourceHistoryRepository.create")
@patch("service_bus.deployment_status_updater.ResourceTemplateRepository.create")
@patch("service_bus.deployment_status_updater.OperationRepository.create")
@patch("service_bus.deployment_status_updater.ResourceRepository.create")
@patch("services.logging.logger.exception")
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


@patch("service_bus.deployment_status_updater.ResourceHistoryRepository.create")
@patch("service_bus.deployment_status_updater.ResourceTemplateRepository.create")
@patch("service_bus.deployment_status_updater.OperationRepository.create")
@patch("service_bus.deployment_status_updater.ResourceRepository.create")
@patch("services.logging.logger.exception")
async def test_when_updating_and_state_store_exception(logging_mock, resource_repo, operation_repo, _, __):
    resource_repo.return_value.get_resource_dict_by_id.side_effect = Exception

    operation = create_sample_operation(test_sb_message["id"], RequestAction.Install)
    operation_repo.return_value.get_operation_by_id.return_value = operation

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(ServiceBusReceivedMessageMock(test_sb_message))

    logging_mock.assert_called_once_with("Failed to update status")
    assert complete_message is False


@patch("service_bus.deployment_status_updater.ResourceHistoryRepository.create")
@patch("service_bus.deployment_status_updater.ResourceTemplateRepository.create")
@patch("service_bus.deployment_status_updater.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
@patch("service_bus.deployment_status_updater.OperationRepository.create")
@patch("service_bus.deployment_status_updater.ResourceRepository.create")
async def test_state_transitions_from_deployed_to_deleted(resource_repo, operations_repo_mock, _, __, ___):
    updated_message = test_sb_message.copy()
    updated_message["status"] = Status.Deleted
    updated_message["message"] = "Has been deleted"
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(updated_message)

    workspace = create_sample_workspace_object(test_sb_message["id"])
    workspace.deploymentStatus = Status.Deployed
    resource_repo.return_value.get_resource_by_id.return_value = workspace
    resource_repo.return_value.get_resource_dict_by_id.return_value = workspace.model_dump()

    operation = create_sample_operation(workspace.id, RequestAction.UnInstall)
    operation.steps[0].status = Status.Deleting
    operations_repo_mock.return_value.get_operation_by_id.return_value = operation

    expected_operation = create_sample_operation(workspace.id, RequestAction.UnInstall)
    expected_operation.steps[0].status = Status.Deleted
    expected_operation.steps[0].message = updated_message["message"]
    expected_operation.steps[0].statusUpdateComplete = True
    expected_operation.status = Status.Deleted
    expected_operation.message = updated_message["message"]

    status_updater = DeploymentStatusUpdater()
    await status_updater.init_repos()
    complete_message = await status_updater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    operations_repo_mock.return_value.update_item.assert_awaited_with(expected_operation)
    assert resource_repo.return_value.update_item.call_args.args[0].deploymentStatus == Status.Deleted


@patch("service_bus.deployment_status_updater.ResourceHistoryRepository.create")
@patch("service_bus.deployment_status_updater.ResourceTemplateRepository.create")
@patch("service_bus.deployment_status_updater.OperationRepository.create")
@patch("service_bus.deployment_status_updater.ResourceRepository.create")
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


@patch("service_bus.deployment_status_updater.ResourceHistoryRepository.create")
@patch("service_bus.deployment_status_updater.ResourceTemplateRepository.create")
@patch("service_bus.deployment_status_updater.OperationRepository.create")
@patch("service_bus.deployment_status_updater.ResourceRepository.create")
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


@patch("service_bus.deployment_status_updater.ResourceHistoryRepository.create")
@patch("service_bus.deployment_status_updater.ResourceTemplateRepository.create")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
@patch("service_bus.deployment_status_updater.OperationRepository.create")
@patch("service_bus.deployment_status_updater.ResourceRepository.create")
@patch("service_bus.helpers.ServiceBusClient")
async def test_multi_step_operation_sends_next_step(
    sb_sender_client,
    resource_repo,
    operations_repo,
    update_resource_for_step,
    _,
    __,
    multi_step_operation,
    user_resource_multi,
    basic_shared_service,
):
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
        user=ANY,
    )
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


@patch("service_bus.deployment_status_updater.ResourceHistoryRepository.create")
@patch("service_bus.deployment_status_updater.ResourceTemplateRepository.create")
@patch("service_bus.deployment_status_updater.OperationRepository.create")
@patch("service_bus.deployment_status_updater.ResourceRepository.create")
@patch("service_bus.helpers.ServiceBusClient")
async def test_multi_step_operation_ends_at_last_step(
    sb_sender_client,
    resource_repo,
    operations_repo,
    _,
    __,
    multi_step_operation,
    user_resource_multi,
    basic_shared_service,
):
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


@patch("service_bus.deployment_status_updater.ResourceHistoryRepository.create")
@patch("service_bus.deployment_status_updater.ResourceTemplateRepository.create")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
@patch("service_bus.deployment_status_updater.OperationRepository.create")
@patch("service_bus.deployment_status_updater.ResourceRepository.create")
@patch("service_bus.helpers.ServiceBusClient")
@pytest.mark.parametrize("child_status", [Status.Deleted, Status.DeletingFailed])
async def test_child_uninstall_controls_parent_deletion(
    sb_sender_client,
    resource_repo,
    operations_repo,
    update_resource_for_step,
    _,
    __,
    multi_step_operation,
    user_resource_multi,
    primary_workspace_service_resource,
    child_status,
):
    operation = copy.deepcopy(multi_step_operation)
    operation.id = OPERATION_ID
    user_resource_multi.id = "0e569b65-7e01-4a0b-a971-a41f5110c0c1"
    primary_workspace_service_resource.id = "dc9b2f53-0784-4c4f-9b73-4a060a385bca"
    parent = WorkspaceService(**primary_workspace_service_resource.model_dump(), workspaceId="test-workspace")
    parent.isEnabled = False
    parent.deploymentStatus = Status.Updated
    operation.action = RequestAction.UnInstall
    operation.steps = operation.steps[:2]
    child_step, parent_step = operation.steps
    child_step.resourceId = user_resource_multi.id
    child_step.resourceAction = RequestAction.UnInstall
    child_step.status = Status.Deleting
    parent_step.resourceId = primary_workspace_service_resource.id
    parent_step.resourceAction = RequestAction.UnInstall
    parent_step.status = Status.AwaitingDeletion
    operation.resourceId = primary_workspace_service_resource.id
    operation.status = Status.PipelineRunning
    for step, resource in [(child_step, user_resource_multi), (parent_step, parent)]:
        step.templateStepId = "main"
        step.sourceTemplateResourceId = resource.id
        step.resourceTemplateName = resource.templateName
        step.resourceType = resource.resourceType
    parent_before = parent_step.model_copy(deep=True)

    message = {
        "operationId": operation.id,
        "stepId": child_step.id,
        "id": child_step.resourceId,
        "status": child_status,
        "message": "Child uninstall result",
    }
    operations_repo.return_value.get_operation_by_id.return_value = operation
    resources = {
        user_resource_multi.id: user_resource_multi,
        parent.id: parent,
    }
    resource_repo.return_value.get_resource_by_id.side_effect = lambda resource_id: resources[str(resource_id)]
    resource_repo.return_value.get_resource_dict_by_id.side_effect = lambda resource_id: resources[
        str(resource_id)
    ].model_dump()
    update_resource_for_step.return_value = parent
    sb_sender_client().get_queue_sender().send_messages = AsyncMock()

    updater = DeploymentStatusUpdater()
    await updater.init_repos()
    complete = await updater.process_message(ServiceBusReceivedMessageMock(message))

    assert complete is True
    saved_operation = operations_repo.return_value.update_item.call_args.args[0]
    expected_parent_status = Status.DeletingFailed if child_status == Status.DeletingFailed else Status.PipelineRunning
    assert saved_operation.status == expected_parent_status
    assert saved_operation.steps[0].status == child_status
    assert saved_operation.steps[0].message == message["message"]
    assert saved_operation.steps[1] == parent_before
    assert user_resource_multi.deploymentStatus == child_status
    assert parent.deploymentStatus == expected_parent_status
    if child_status == Status.DeletingFailed:
        update_resource_for_step.assert_not_called()
        sb_sender_client().get_queue_sender().send_messages.assert_not_called()
    else:
        update_resource_for_step.assert_called_once()
        sb_sender_client().get_queue_sender().send_messages.assert_called_once()


async def test_convert_outputs_to_dict():
    # Test case 1: Empty list of outputs
    outputs_list = []
    expected_result = {}

    status_updater = DeploymentStatusUpdater()
    assert status_updater.convert_outputs_to_dict(outputs_list) == expected_result

    # Test case 2: List of outputs with mixed types
    deployment_status_update_message = TypeAdapter(DeploymentStatusUpdateMessage).validate_python(
        test_sb_message_with_outputs
    )

    expected_result = {
        "string1": "value1",
        "string2": "value2",
        "boolean1": True,
        "boolean2": True,
        "boolean3": True,
        "list1": "['one', 'two']",
        "list2": ["one", "two"],
    }
    assert status_updater.convert_outputs_to_dict(deployment_status_update_message.outputs) == expected_result


@pytest.mark.parametrize(
    "phase, message_status, expected_operation_status, expected_primary_status",
    [
        ("main", Status.Deleted, Status.PipelineRunning, Status.PipelineRunning),
        ("final", Status.Updated, Status.Deleted, Status.Deleted),
        ("final", Status.UpdatingFailed, Status.DeletingFailed, Status.DeletingFailed),
        ("enqueue_failed", Status.Deleted, Status.DeletingFailed, Status.DeletingFailed),
    ],
)
async def test_uninstall_waits_for_final_pipeline_step(
    phase, message_status, expected_operation_status, expected_primary_status
):
    primary_id = "d9236f8f-7fbb-46d3-9c94-dea6daf32b7f"
    dependency_id = "7af8f146-d751-4587-a22e-eb44c1c6fbe2"
    primary = create_sample_workspace_object(primary_id)
    primary.isEnabled = False
    primary.deploymentStatus = Status.PipelineRunning if phase == "final" else Status.Deleting
    dependency = create_sample_workspace_object(dependency_id)
    dependency.deploymentStatus = Status.Updating
    stored = {primary_id: primary, dependency_id: dependency}

    operation = create_sample_operation(primary_id, RequestAction.UnInstall)
    operation.steps[0].status = Status.Deleted if phase == "final" else Status.Deleting
    operation.steps.append(
        OperationStep(
            id="firewall-step",
            templateStepId="remove-firewall-rules",
            resourceId=dependency_id,
            resourceAction=RequestAction.Upgrade,
            sourceTemplateResourceId=primary_id,
            status=Status.Updating if phase == "final" else Status.AwaitingUpdate,
        )
    )
    operation.status = Status.PipelineRunning
    current_step = operation.steps[1 if phase == "final" else 0]
    message = DeploymentStatusUpdateMessage(
        operationId=operation.id,
        stepId=current_step.id,
        id=current_step.resourceId,
        status=message_status,
        message="Final firewall update failed" if message_status == Status.UpdatingFailed else "Completed",
    )

    updater = DeploymentStatusUpdater()
    updater.operations_repo = AsyncMock()
    updater.operations_repo.get_operation_by_id.return_value = operation
    updater.resource_repo = AsyncMock()
    updater.resource_template_repo = AsyncMock()
    updater.resource_history_repo = AsyncMock()
    updater.resource_repo.get_resource_by_id.side_effect = lambda resource_id: stored[str(resource_id)].model_copy(
        deep=True
    )
    updater.resource_repo.get_resource_dict_by_id.side_effect = lambda resource_id: stored[
        str(resource_id)
    ].model_dump()

    def save_resource(resource):
        stored[resource.id] = resource.model_copy(deep=True)

    def save_resource_dict(resource):
        stored[resource["id"]] = stored[resource["id"]].model_copy(update=resource, deep=True)

    updater.resource_repo.update_item.side_effect = save_resource
    updater.resource_repo.update_item_dict.side_effect = save_resource_dict
    with (
        patch("service_bus.deployment_status_updater.update_resource_for_step", return_value=dependency),
        patch("service_bus.deployment_status_updater.send_deployment_message", new_callable=AsyncMock) as send,
    ):
        if phase == "enqueue_failed":
            send.side_effect = RuntimeError("Cannot enqueue final step")
        assert await updater.update_status_in_database(message) is True

    assert operation.status == expected_operation_status
    assert stored[primary_id].deploymentStatus == expected_primary_status
    assert stored[primary_id].isEnabled is False
    if phase != "final":
        assert stored[primary_id].deploymentStatus != Status.Deleted
        send.assert_awaited_once()
    else:
        assert stored[dependency_id].deploymentStatus == message_status
        send.assert_not_awaited()
    if message_status == Status.UpdatingFailed:
        assert operation.message == "Multi step pipeline failed on step remove-firewall-rules"
        assert operation.steps[-1].message == "Final firewall update failed"
    if phase == "enqueue_failed":
        assert operation.steps[-1].status == Status.UpdatingFailed
        assert "Cannot enqueue final step" in operation.steps[-1].message


@pytest.fixture
def persisted_uninstall_pipeline():
    primary = create_sample_workspace_object("d9236f8f-7fbb-46d3-9c94-dea6daf32b7f")
    primary.isEnabled = False
    primary.deploymentStatus = Status.Deleting
    dependency = create_sample_workspace_object("7af8f146-d751-4587-a22e-eb44c1c6fbe2")
    dependency.deploymentStatus = Status.Updated
    operation = create_sample_operation(primary.id, RequestAction.UnInstall)
    operation.status = Status.PipelineRunning
    operation.steps[0].status = Status.Deleting
    operation.steps.append(
        OperationStep(
            id="firewall-step",
            templateStepId="remove-firewall-rules",
            resourceId=dependency.id,
            resourceAction=RequestAction.Upgrade,
            sourceTemplateResourceId=primary.id,
            status=Status.AwaitingUpdate,
        )
    )
    stored = {"operation": operation, "resources": {primary.id: primary, dependency.id: dependency}}
    updater = DeploymentStatusUpdater()
    updater.operations_repo = AsyncMock()
    updater.resource_repo = AsyncMock()
    updater.resource_template_repo = AsyncMock()
    updater.resource_history_repo = AsyncMock()
    updater.operations_repo.get_operation_by_id.side_effect = lambda _: stored["operation"].model_copy(deep=True)

    def save_operation(item):
        stored["operation"] = item.model_copy(deep=True)

    def save_resource(item):
        stored["resources"][item.id] = item.model_copy(deep=True)

    def save_resource_dict(item):
        original = stored["resources"][item["id"]]
        stored["resources"][item["id"]] = original.model_copy(update=item, deep=True)

    updater.operations_repo.update_item.side_effect = save_operation
    updater.resource_repo.get_resource_by_id.side_effect = lambda item_id: stored["resources"][str(item_id)].model_copy(
        deep=True
    )
    updater.resource_repo.get_resource_dict_by_id.side_effect = lambda item_id: stored["resources"][
        str(item_id)
    ].model_dump()
    updater.resource_repo.update_item.side_effect = save_resource
    updater.resource_repo.update_item_dict.side_effect = save_resource_dict

    def message(step_index, status):
        step = stored["operation"].steps[step_index]
        return DeploymentStatusUpdateMessage(
            operationId=operation.id, stepId=step.id, id=step.resourceId, status=status, message="Result"
        )

    with (
        patch("service_bus.deployment_status_updater.update_resource_for_step", return_value=dependency),
        patch("service_bus.deployment_status_updater.send_deployment_message", new_callable=AsyncMock) as send,
    ):
        yield updater, stored, message, send


async def test_uninstall_redelivery_does_not_dispatch_next_step_twice(persisted_uninstall_pipeline):
    updater, stored, message, send = persisted_uninstall_pipeline
    callback = message(0, Status.Deleted)
    assert await updater.update_status_in_database(callback) is True
    assert stored["operation"].steps[0].statusUpdateComplete is True
    before = copy.deepcopy(stored)

    assert await updater.update_status_in_database(callback) is True

    assert stored == before
    send.assert_awaited_once()


@pytest.mark.parametrize("final_status", [Status.Updated, Status.UpdatingFailed])
@pytest.mark.parametrize(
    "callback_index, callback_status",
    [(0, Status.Deleted), (0, Status.Deleting), (1, Status.Updating), (1, Status.Updated)],
)
async def test_uninstall_redelivery_preserves_final_outcome(
    persisted_uninstall_pipeline, final_status, callback_index, callback_status
):
    updater, stored, message, send = persisted_uninstall_pipeline
    assert await updater.update_status_in_database(message(0, Status.Deleted)) is True
    assert await updater.update_status_in_database(message(1, final_status)) is True
    before = copy.deepcopy(stored)

    assert await updater.update_status_in_database(message(callback_index, callback_status)) is True

    assert stored == before
    send.assert_awaited_once()


@pytest.mark.parametrize("later_status", [Status.Updating, Status.Updated, Status.UpdatingFailed])
async def test_uninstall_older_callback_does_not_repeat_writes_after_later_progress(
    persisted_uninstall_pipeline, later_status
):
    updater, stored, message, send = persisted_uninstall_pipeline
    # Older operations have no checkpoint. A later callback also proves dispatch
    # completed if the process stopped before it could save the checkpoint.
    operation = stored["operation"]
    operation.steps[0].status = Status.Deleted
    operation.steps[1].status = later_status
    operation.status = {
        Status.Updating: Status.PipelineRunning,
        Status.Updated: Status.Deleted,
        Status.UpdatingFailed: Status.DeletingFailed,
    }[later_status]
    legacy = operation.model_dump()
    for step in legacy["steps"]:
        del step["statusUpdateComplete"]
    stored["operation"] = Operation.model_validate(legacy)
    before = copy.deepcopy(stored)

    assert await updater.update_status_in_database(message(0, Status.Deleted)) is True

    if later_status == Status.UpdatingFailed:
        # A legacy record can also be an interrupted dispatch-failure write.
        # Only the saved root outcome and the earlier checkpoint need repair.
        before["operation"].steps[0].statusUpdateComplete = True
        before["resources"][operation.resourceId].deploymentStatus = Status.DeletingFailed
        updater.resource_repo.update_item.assert_awaited_once_with(before["resources"][operation.resourceId])
    else:
        updater.resource_repo.update_item.assert_not_awaited()
    assert stored == before
    updater.resource_repo.update_item_dict.assert_not_awaited()
    send.assert_not_awaited()


@pytest.mark.parametrize("write_method", ["update_item", "update_item_dict"])
async def test_uninstall_redelivery_resumes_after_partial_resource_write(persisted_uninstall_pipeline, write_method):
    updater, stored, message, send = persisted_uninstall_pipeline
    writer = getattr(updater.resource_repo, write_method)
    save = writer.side_effect
    writer.side_effect = RuntimeError("Interrupted database write")
    callback = message(0, Status.Deleted)
    assert await updater.update_status_in_database(callback) is False
    assert stored["operation"].steps[0].status == Status.Deleted
    assert stored["operation"].steps[0].statusUpdateComplete is False
    send.assert_not_awaited()

    writer.side_effect = save
    assert await updater.update_status_in_database(callback) is True

    assert stored["operation"].steps[0].statusUpdateComplete is True
    assert stored["resources"][str(callback.id)].deploymentStatus == Status.PipelineRunning
    send.assert_awaited_once()


@pytest.mark.parametrize("final_status", [Status.Updated, Status.UpdatingFailed])
async def test_uninstall_redelivery_finishes_terminal_resource_write(persisted_uninstall_pipeline, final_status):
    updater, stored, message, send = persisted_uninstall_pipeline
    assert await updater.update_status_in_database(message(0, Status.Deleted)) is True
    writer = updater.resource_repo.update_item
    save = writer.side_effect

    def fail_primary_write(item):
        if item.id == stored["operation"].resourceId:
            raise RuntimeError("Interrupted primary resource write")
        save(item)

    writer.side_effect = fail_primary_write
    callback = message(1, final_status)
    assert await updater.update_status_in_database(callback) is False
    assert stored["operation"].steps[1].statusUpdateComplete is False

    writer.side_effect = save
    assert await updater.update_status_in_database(callback) is True

    expected = Status.Deleted if final_status == Status.Updated else Status.DeletingFailed
    assert stored["operation"].status == expected
    assert stored["operation"].steps[1].statusUpdateComplete is True
    assert stored["resources"][stored["operation"].resourceId].deploymentStatus == expected
    send.assert_awaited_once()


@pytest.fixture(params=["primary", "dependency", "single"])
def pending_final_uninstall_callback(persisted_uninstall_pipeline, request):
    updater, stored, message, send = persisted_uninstall_pipeline
    operation = stored["operation"]
    primary_id = operation.resourceId
    dependency_id = operation.steps[1].resourceId
    operation.steps[0].statusUpdateComplete = True
    stored["resources"][primary_id].deploymentStatus = Status.PipelineRunning

    if request.param == "single":
        operation.steps = operation.steps[:1]
        operation.steps[0].statusUpdateComplete = False
        operation.status = Status.Deleting
        stored["resources"][primary_id].deploymentStatus = Status.Deleting
        final_status = Status.Deleted
    elif request.param == "primary":
        operation.steps[0].resourceId = dependency_id
        operation.steps[0].resourceAction = RequestAction.Upgrade
        operation.steps[0].status = Status.Updated
        operation.steps[1].resourceId = primary_id
        operation.steps[1].resourceAction = RequestAction.UnInstall
        operation.steps[1].status = Status.Deleting
        final_status = Status.Deleted
    else:
        operation.steps[0].status = Status.Deleted
        operation.steps[1].status = Status.Updating
        final_status = Status.Updated

    callback = message(len(operation.steps) - 1, final_status)
    callback.outputs = [Output(Name="final_output", Value="saved", Type="string")]
    return updater, stored, callback, send


@pytest.mark.parametrize("failed_write", ["outputs", "final_operation", "final_status"])
async def test_final_uninstall_redelivery_keeps_root_visible_until_outputs_are_saved(
    pending_final_uninstall_callback, failed_write
):
    updater, stored, callback, send = pending_final_uninstall_callback
    primary_id = stored["operation"].resourceId
    pending_status = Status.Deleting if len(stored["operation"].steps) == 1 else Status.PipelineRunning
    writer = {
        "outputs": updater.resource_repo.update_item_dict,
        "final_operation": updater.operations_repo.update_item,
        "final_status": updater.resource_repo.update_item,
    }[failed_write]
    save = writer.side_effect

    def interrupt_write(item):
        if (
            failed_write == "outputs"
            or (failed_write == "final_operation" and item.status == Status.Deleted)
            or (failed_write == "final_status" and item.id == primary_id and item.deploymentStatus == Status.Deleted)
        ):
            raise RuntimeError("Interrupted final callback write")
        save(item)

    writer.side_effect = interrupt_write
    assert await updater.update_status_in_database(callback) is False

    assert stored["resources"][primary_id].deploymentStatus == pending_status
    expected_operation_status = Status.Deleted if failed_write == "final_status" else pending_status
    assert stored["operation"].status == expected_operation_status
    assert stored["operation"].steps[-1].statusUpdateComplete is False
    output_resource = stored["resources"][str(callback.id)]
    if failed_write == "outputs":
        assert "final_output" not in output_resource.properties
    else:
        assert output_resource.properties["final_output"] == "saved"
    send.assert_not_awaited()

    writer.side_effect = save
    assert await updater.update_status_in_database(callback) is True

    assert stored["resources"][str(callback.id)].properties["final_output"] == "saved"
    assert stored["resources"][primary_id].deploymentStatus == Status.Deleted
    assert stored["operation"].status == Status.Deleted
    assert stored["operation"].message == (
        callback.message if len(stored["operation"].steps) == 1 else "Multi step pipeline completed successfully"
    )
    assert stored["operation"].steps[-1].statusUpdateComplete is True
    send.assert_not_awaited()

    before = copy.deepcopy(stored)
    updater.resource_repo.update_item.reset_mock()
    updater.resource_repo.update_item_dict.reset_mock()
    assert await updater.update_status_in_database(callback) is True
    assert stored == before
    updater.resource_repo.update_item.assert_not_awaited()
    updater.resource_repo.update_item_dict.assert_not_awaited()


@pytest.mark.parametrize("final_status", [Status.Deleted, Status.DeletingFailed])
@pytest.mark.parametrize("callback_status", [Status.Deleted, Status.Deleting, Status.DeletingFailed])
async def test_single_step_uninstall_redelivery_preserves_final_outcome(
    persisted_uninstall_pipeline, final_status, callback_status
):
    updater, stored, message, send = persisted_uninstall_pipeline
    stored["operation"].steps = stored["operation"].steps[:1]
    stored["operation"].status = Status.Deleting
    assert await updater.update_status_in_database(message(0, final_status)) is True
    assert stored["operation"].status == final_status
    assert stored["resources"][stored["operation"].resourceId].deploymentStatus == final_status
    assert stored["operation"].steps[0].statusUpdateComplete is True
    before = copy.deepcopy(stored)

    assert await updater.update_status_in_database(message(0, callback_status)) is True

    assert stored == before
    send.assert_not_awaited()


async def test_uninstall_checkpoint_failure_does_not_report_dispatch_failure(persisted_uninstall_pipeline):
    updater, stored, message, send = persisted_uninstall_pipeline
    writer = updater.operations_repo.update_item
    save = writer.side_effect

    def fail_checkpoint(item):
        if item.steps[0].statusUpdateComplete:
            raise RuntimeError("Interrupted checkpoint write")
        save(item)

    writer.side_effect = fail_checkpoint
    assert await updater.update_status_in_database(message(0, Status.Deleted)) is False

    assert stored["operation"].status == Status.PipelineRunning
    assert stored["operation"].steps[1].status == Status.AwaitingUpdate
    assert stored["operation"].steps[0].statusUpdateComplete is False
    send.assert_awaited_once()


async def test_uninstall_redelivery_repairs_root_after_dispatch_failure(persisted_uninstall_pipeline):
    updater, stored, message, send = persisted_uninstall_pipeline
    send.side_effect = RuntimeError("Cannot enqueue final step")
    writer = updater.resource_repo.update_item
    save = writer.side_effect

    def fail_failure_write(item):
        if item.deploymentStatus == Status.DeletingFailed:
            raise RuntimeError("Interrupted root failure write")
        save(item)

    writer.side_effect = fail_failure_write
    callback = message(0, Status.Deleted)
    assert await updater.update_status_in_database(callback) is False
    assert stored["operation"].status == Status.DeletingFailed
    assert stored["resources"][str(callback.id)].deploymentStatus == Status.PipelineRunning
    assert stored["operation"].steps[0].statusUpdateComplete is False
    updater.resource_repo.update_item_dict.reset_mock()

    writer.side_effect = save
    assert await updater.update_status_in_database(callback) is True

    assert stored["resources"][str(callback.id)].deploymentStatus == Status.DeletingFailed
    assert stored["operation"].steps[0].statusUpdateComplete is True
    updater.resource_repo.update_item_dict.assert_not_awaited()
    send.assert_awaited_once()


STEP_STATUSES = {
    RequestAction.Install: (Status.Deploying, Status.Deployed, Status.DeploymentFailed),
    RequestAction.Upgrade: (Status.Updating, Status.Updated, Status.UpdatingFailed),
    "restart": (Status.InvokingAction, Status.ActionSucceeded, Status.ActionFailed),
    RequestAction.UnInstall: (Status.Deleting, Status.Deleted, Status.DeletingFailed),
}


@pytest.fixture(params=list(STEP_STATUSES), ids=str)
def persisted_pipeline(request):
    """A main step followed by a firewall step, with operation and resource writes kept in memory."""
    action = request.param
    primary = create_sample_workspace_object("d9236f8f-7fbb-46d3-9c94-dea6daf32b7f")
    firewall = create_sample_workspace_object("7af8f146-d751-4587-a22e-eb44c1c6fbe2")
    operation = create_sample_operation(primary.id, action)
    operation.steps[0].status = Status.AwaitingAction
    operation.steps.append(
        OperationStep(
            id="firewall-step",
            templateStepId="firewall",
            resourceId=firewall.id,
            resourceAction=RequestAction.Upgrade,
            sourceTemplateResourceId=primary.id,
            status=Status.AwaitingUpdate,
        )
    )
    stored = {"operation": operation, "resources": {primary.id: primary, firewall.id: firewall}}
    updater = DeploymentStatusUpdater()
    updater.operations_repo = AsyncMock()
    updater.resource_repo = AsyncMock()
    updater.resource_template_repo = AsyncMock()
    updater.resource_history_repo = AsyncMock()
    updater.operations_repo.get_operation_by_id.side_effect = lambda _: stored["operation"].model_copy(deep=True)
    updater.operations_repo.update_item.side_effect = lambda item: stored.update(operation=item.model_copy(deep=True))
    updater.resource_repo.get_resource_by_id.side_effect = lambda item_id: stored["resources"][str(item_id)].model_copy(
        deep=True
    )
    updater.resource_repo.get_resource_dict_by_id.side_effect = lambda item_id: stored["resources"][
        str(item_id)
    ].model_dump()

    def save_resource(item):
        stored["resources"][item.id] = item.model_copy(deep=True)

    def save_resource_dict(item):
        stored["resources"][item["id"]] = stored["resources"][item["id"]].model_copy(update=item, deep=True)

    updater.resource_repo.update_item.side_effect = save_resource
    updater.resource_repo.update_item_dict.side_effect = save_resource_dict

    def message(status, execution_id="run-a", step_index=0):
        step = stored["operation"].steps[step_index]
        return DeploymentStatusUpdateMessage(
            operationId=operation.id,
            stepId=step.id,
            id=step.resourceId,
            status=status,
            message=f"{status} from {execution_id}",
            executionId=execution_id,
        )

    with (
        patch("service_bus.deployment_status_updater.update_resource_for_step", return_value=firewall),
        patch("service_bus.deployment_status_updater.send_deployment_message", new_callable=AsyncMock) as send,
    ):
        yield updater, stored, message, send, STEP_STATUSES[action]


@pytest.mark.parametrize("final_index", [1, 2])
async def test_a_status_from_another_run_does_not_replace_the_final_status(persisted_pipeline, final_index):
    updater, stored, message, send, step_statuses = persisted_pipeline
    assert await updater.update_status_in_database(message(step_statuses[0])) is True
    assert await updater.update_status_in_database(message(step_statuses[final_index])) is True
    assert stored["operation"].steps[0].executionId == "run-a"
    before = copy.deepcopy(stored)

    for status in step_statuses:
        assert await updater.update_status_in_database(message(status, execution_id="run-b")) is True

    assert stored == before
    assert send.await_count == (1 if final_index == 1 else 0)


async def test_a_later_status_from_the_finished_run_is_ignored(persisted_pipeline):
    updater, stored, message, send, (in_progress, success, failure) = persisted_pipeline
    assert await updater.update_status_in_database(message(success)) is True
    before = copy.deepcopy(stored)

    assert await updater.update_status_in_database(message(in_progress)) is True
    assert await updater.update_status_in_database(message(failure)) is True

    assert stored == before
    send.assert_awaited_once()


async def test_a_repeated_final_status_does_not_dispatch_the_next_step_twice(persisted_pipeline):
    updater, stored, message, send, (_, success, _) = persisted_pipeline
    assert await updater.update_status_in_database(message(success)) is True
    assert stored["operation"].steps[0].statusUpdateComplete is True
    before = copy.deepcopy(stored)

    assert await updater.update_status_in_database(message(success)) is True

    assert stored == before
    send.assert_awaited_once()


async def test_a_repeated_final_status_finishes_the_writes_of_the_first_copy(persisted_pipeline):
    updater, stored, message, send, (_, success, _) = persisted_pipeline
    save = updater.resource_repo.update_item.side_effect
    writes = []

    def fail_first_write(item):
        writes.append(item.id)
        if len(writes) == 1:
            raise RuntimeError("Cosmos DB is not available")
        save(item)

    updater.resource_repo.update_item.side_effect = fail_first_write
    assert await updater.update_status_in_database(message(success)) is False
    assert stored["operation"].steps[0].status == success
    assert stored["operation"].steps[0].statusUpdateComplete is False
    send.assert_not_awaited()

    assert await updater.update_status_in_database(message(success)) is True

    assert stored["operation"].steps[0].statusUpdateComplete is True
    send.assert_awaited_once()


async def test_a_new_run_before_the_final_status_takes_over_the_step(persisted_pipeline):
    updater, stored, message, send, (in_progress, success, _) = persisted_pipeline
    assert await updater.update_status_in_database(message(in_progress, execution_id="run-a")) is True
    assert await updater.update_status_in_database(message(in_progress, execution_id="run-b")) is True
    assert stored["operation"].steps[0].executionId == "run-b"

    assert await updater.update_status_in_database(message(success, execution_id="run-b")) is True
    assert await updater.update_status_in_database(message(success, execution_id="run-a")) is True

    assert stored["operation"].steps[0].executionId == "run-b"
    assert stored["operation"].steps[0].message == f"{success} from run-b"
    send.assert_awaited_once()


# An uninstall keeps the earlier rule for a final step from #5253.
@pytest.mark.parametrize("persisted_pipeline", [RequestAction.Install, RequestAction.Upgrade, "restart"], indirect=True)
async def test_the_first_run_replaces_a_failure_that_the_api_wrote(persisted_pipeline):
    updater, stored, message, send, (in_progress, success, failure) = persisted_pipeline
    # For example, the API failed a step that it could not resend, but the resource processor got the first message.
    stored["operation"].steps[0].status = failure
    stored["operation"].steps[0].message = "written by the API"

    assert await updater.update_status_in_database(message(in_progress)) is True
    assert stored["operation"].steps[0].status == in_progress
    assert await updater.update_status_in_database(message(success)) is True

    assert stored["operation"].steps[0].status == success
    assert stored["operation"].steps[0].executionId == "run-a"
    send.assert_awaited_once()


async def test_a_message_without_an_execution_id_keeps_the_earlier_rules():
    workspace = create_sample_workspace_object("d9236f8f-7fbb-46d3-9c94-dea6daf32b7f")
    operation = create_sample_operation(workspace.id, RequestAction.Install)
    operation.steps[0].status = Status.Deployed
    updater = DeploymentStatusUpdater()
    updater.operations_repo = AsyncMock()
    updater.operations_repo.get_operation_by_id.return_value = operation
    updater.resource_repo = AsyncMock()
    updater.resource_repo.get_resource_by_id.return_value = workspace
    message = DeploymentStatusUpdateMessage(
        operationId=operation.id,
        stepId=operation.steps[0].id,
        id=workspace.id,
        status=Status.DeploymentFailed,
        message="failed",
    )

    assert await updater.update_status_in_database(message) is True

    assert operation.steps[0].status == Status.DeploymentFailed
    assert operation.steps[0].executionId is None


@patch("service_bus.deployment_status_updater.logger")
async def test_an_ignored_status_is_not_logged_as_a_database_update(logger, persisted_pipeline):
    updater, _, message, _, (_, success, failure) = persisted_pipeline
    assert await updater.update_status_in_database(message(success)) is True
    logger.reset_mock()

    assert await updater.update_status_in_database(message(failure, execution_id="run-b")) is True

    logged = " ".join(str(call.args[0]) for call in logger.info.call_args_list)
    assert "Ignoring a status from another run" in logged
    assert "Update status in DB" not in logged
