import asyncio
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from db.errors import EntityDoesNotExist
from db.repositories.operations import PENDING_DISPATCH
from models.domain.operation import Status
from models.domain.workspace import Workspace
from resources import strings
from service_bus.deployment_status_updater import (
    NOT_SENT_BEFORE_A_LATER_REQUEST,
    NOT_SENT_WITH_SENSITIVE_VALUES,
    DeploymentStatusUpdater,
)
from tests_ma.test_service_bus.test_deployment_status_update import OPERATION_ID, create_sample_operation

pytestmark = pytest.mark.asyncio

RESOURCE_ID = "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76"
FIREWALL_ID = "a8b2c3d4-1111-4222-8333-944455556666"
CHILD_ID = "c3d4e5f6-2222-4333-8444-a55566667777"
MESSAGE_ID = f"{OPERATION_ID}:random-uuid"
AWAITING = {
    "install": Status.AwaitingDeployment,
    "upgrade": Status.AwaitingUpdate,
    "uninstall": Status.AwaitingDeletion,
    "start": Status.AwaitingAction,
}


def pending_document(action="install", status=Status.AwaitingDeployment, sensitive_values=False):
    operation = create_sample_operation(RESOURCE_ID, action)
    operation.steps[0].status = status
    document = operation.model_dump()
    document["_etag"] = "etag"
    document[PENDING_DISPATCH] = {
        "stepId": "random-uuid",
        "messageId": MESSAGE_ID,
        "createdWhen": 1.0,
        "sensitiveValues": sensitive_values,
    }
    return document


def workspace(properties):
    return Workspace(
        id=RESOURCE_ID,
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties=properties,
        resourcePath="test",
    )


@pytest.fixture
def updater():
    updater = DeploymentStatusUpdater()
    updater.operations_repo = AsyncMock()
    updater.resource_repo = AsyncMock()
    updater.resource_template_repo = AsyncMock()
    updater.resource_history_repo = AsyncMock()
    updater.operations_repo.claim_pending_dispatch.return_value = True
    updater.resource_repo.get_resource_by_id.return_value = workspace({})
    updater.operations_repo.get_later_operations_for_resource.return_value = []
    return updater


@patch("service_bus.deployment_status_updater.send_deployment_message")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
async def test_sends_the_pending_message_then_clears_the_entry(update_mock, send_mock, updater):
    calls = []
    update_mock.return_value = workspace({"display_name": "name"})
    send_mock.side_effect = lambda **kwargs: calls.append("send")
    updater.operations_repo.clear_pending_dispatch.side_effect = lambda *args: calls.append("clear")

    await updater.resend_pending_dispatch(pending_document())

    kwargs = send_mock.await_args.kwargs
    assert kwargs["message_id"] == MESSAGE_ID
    assert kwargs["correlation_id"] == OPERATION_ID
    assert kwargs["session_id"] == RESOURCE_ID
    assert json.loads(kwargs["content"])["stepId"] == "random-uuid"
    updater.operations_repo.clear_pending_dispatch.assert_awaited_once_with(OPERATION_ID, MESSAGE_ID)
    assert calls == ["send", "clear"]


@patch("service_bus.deployment_status_updater.send_deployment_message")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
async def test_an_entry_that_another_instance_claimed_is_left(update_mock, send_mock, updater):
    updater.operations_repo.claim_pending_dispatch.return_value = False

    await updater.resend_pending_dispatch(pending_document())

    update_mock.assert_not_awaited()
    send_mock.assert_not_awaited()
    updater.operations_repo.clear_pending_dispatch.assert_not_awaited()


@patch("service_bus.deployment_status_updater.send_deployment_message")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
async def test_a_step_with_a_status_only_clears_the_entry(update_mock, send_mock, updater):
    await updater.resend_pending_dispatch(pending_document(status=Status.Deploying))

    send_mock.assert_not_awaited()
    updater.operations_repo.clear_pending_dispatch.assert_awaited_once_with(OPERATION_ID, MESSAGE_ID)


@pytest.mark.parametrize(
    "action, status, failed",
    [
        ("install", Status.AwaitingDeployment, Status.DeploymentFailed),
        ("upgrade", Status.AwaitingUpdate, Status.UpdatingFailed),
    ],
)
@patch("service_bus.deployment_status_updater.send_deployment_message")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
async def test_a_first_message_with_sensitive_values_fails_the_step(
    update_mock, send_mock, updater, action, status, failed
):
    # The API built that message from the resource in memory. Cosmos DB has only the placeholder.
    await updater.resend_pending_dispatch(pending_document(action=action, status=status, sensitive_values=True))

    update_mock.assert_not_awaited()
    send_mock.assert_not_awaited()
    operation = updater.operations_repo.update_item.await_args.args[0]
    assert operation.steps[0].status == failed
    assert operation.steps[0].message == NOT_SENT_WITH_SENSITIVE_VALUES
    assert operation.status == failed
    assert updater.resource_repo.update_item.await_args.args[0].deploymentStatus == failed


@patch("service_bus.deployment_status_updater.send_deployment_message")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
async def test_sensitive_values_of_another_resource_do_not_stop_the_send(update_mock, send_mock, updater):
    # The API builds the message of a step for another resource from Cosmos DB, so a resend has the same values.
    document = pending_document(sensitive_values=True)
    document["steps"][0]["resourceId"] = "another-resource"
    update_mock.return_value = workspace({"display_name": "name"})

    await updater.resend_pending_dispatch(document)

    send_mock.assert_awaited_once()
    updater.operations_repo.update_item.assert_not_awaited()


@pytest.mark.parametrize("action", ["install", "upgrade", "uninstall", "start"])
@patch("service_bus.deployment_status_updater.send_deployment_message")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
async def test_a_resend_without_sensitive_values_sends_the_placeholder(update_mock, send_mock, updater, action):
    # The first message had no real sensitive values, so it had the same placeholder as Cosmos DB.
    update_mock.return_value = workspace({"settings": {"secret": strings.REDACTED_SENSITIVE_VALUE}})

    await updater.resend_pending_dispatch(pending_document(action=action, status=AWAITING[action]))

    send_mock.assert_awaited_once()
    updater.operations_repo.update_item.assert_not_awaited()
    updater.operations_repo.clear_pending_dispatch.assert_awaited_once_with(OPERATION_ID, MESSAGE_ID)


@patch("service_bus.deployment_status_updater.send_deployment_message")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
async def test_a_later_request_for_the_resource_fails_the_step(update_mock, send_mock, updater):
    document = pending_document()
    later = create_sample_operation(RESOURCE_ID, "uninstall")
    later.createdWhen = document["createdWhen"] + 60
    updater.operations_repo.get_later_operations_for_resource.return_value = [later]

    await updater.resend_pending_dispatch(document)

    updater.operations_repo.get_later_operations_for_resource.assert_awaited_once_with(
        RESOURCE_ID, document["createdWhen"]
    )
    update_mock.assert_not_awaited()
    send_mock.assert_not_awaited()
    operation = updater.operations_repo.update_item.await_args.args[0]
    assert operation.steps[0].status == Status.DeploymentFailed
    assert operation.steps[0].message == NOT_SENT_BEFORE_A_LATER_REQUEST
    assert operation.status == Status.DeploymentFailed
    # The later request owns the status of the resource, for example a resource that it deleted.
    updater.resource_repo.update_item.assert_not_awaited()


@patch("service_bus.deployment_status_updater.send_deployment_message")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
async def test_a_later_request_for_the_first_child_of_a_cascade_fails_the_step(update_mock, send_mock, updater):
    # A disable of a workspace service starts with the main step of its user resource. A user can delete the user
    # resource at once, because the cascade already disabled it.
    document = pending_document(action="upgrade", status=Status.AwaitingUpdate)
    document["steps"][0]["resourceId"] = CHILD_ID
    document["steps"][0]["sourceTemplateResourceId"] = CHILD_ID
    later = create_sample_operation(CHILD_ID, "uninstall")
    later.createdWhen = document["createdWhen"] + 60
    updater.operations_repo.get_later_operations_for_resource.side_effect = lambda resource_id, _: (
        [later] if resource_id == CHILD_ID else []
    )
    update_mock.return_value = workspace({})

    await updater.resend_pending_dispatch(document)

    queried = [call.args for call in updater.operations_repo.get_later_operations_for_resource.await_args_list]
    assert queried == [(RESOURCE_ID, document["createdWhen"]), (CHILD_ID, document["createdWhen"])]
    update_mock.assert_not_awaited()
    send_mock.assert_not_awaited()
    operation = updater.operations_repo.update_item.await_args.args[0]
    assert operation.steps[0].status == Status.UpdatingFailed
    assert operation.steps[0].message == NOT_SENT_BEFORE_A_LATER_REQUEST
    updater.resource_repo.update_item.assert_not_awaited()


@patch("service_bus.deployment_status_updater.send_deployment_message")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
async def test_a_later_request_comes_before_the_sensitive_values(update_mock, send_mock, updater):
    # A later delete owns the status of the resource, so the sensitive value rule must not set it to failed again.
    document = pending_document(sensitive_values=True)
    later = create_sample_operation(RESOURCE_ID, "uninstall")
    later.createdWhen = document["createdWhen"] + 60
    updater.operations_repo.get_later_operations_for_resource.return_value = [later]

    await updater.resend_pending_dispatch(document)

    send_mock.assert_not_awaited()
    assert updater.operations_repo.update_item.await_args.args[0].message == NOT_SENT_BEFORE_A_LATER_REQUEST
    updater.resource_repo.update_item.assert_not_awaited()


@patch("service_bus.deployment_status_updater.send_deployment_message")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
async def test_a_failed_first_step_on_another_resource_changes_only_the_resource_of_the_request(
    update_mock, send_mock, updater
):
    # For example, the first step of an install pipeline is an upgrade of the firewall. That step did not run.
    document = pending_document()
    document["steps"][0]["resourceId"] = FIREWALL_ID
    document["steps"][0]["resourceAction"] = "upgrade"
    document["steps"][0]["status"] = Status.AwaitingUpdate
    update_mock.side_effect = Exception("template not found")

    await updater.resend_pending_dispatch(document)

    # The firewall has many requests, so only later requests on the resource of the request count.
    updater.operations_repo.get_later_operations_for_resource.assert_awaited_once_with(
        RESOURCE_ID, document["createdWhen"]
    )
    operation = updater.operations_repo.update_item.await_args.args[0]
    assert operation.steps[0].status == Status.UpdatingFailed
    assert operation.status == Status.DeploymentFailed
    updater.resource_repo.get_resource_by_id.assert_awaited_once_with(uuid.UUID(RESOURCE_ID))
    assert updater.resource_repo.update_item.await_args.args[0].deploymentStatus == Status.DeploymentFailed


@patch("service_bus.deployment_status_updater.send_deployment_message")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
async def test_a_missing_resource_still_removes_the_entry(update_mock, send_mock, updater):
    update_mock.side_effect = Exception("template not found")
    updater.resource_repo.get_resource_by_id.side_effect = EntityDoesNotExist

    await updater.resend_pending_dispatch(pending_document())

    # The operation write removes the entry, so the next pass does not claim it again.
    assert updater.operations_repo.update_item.await_args.args[0].status == Status.DeploymentFailed
    updater.resource_repo.update_item.assert_not_awaited()


@patch("service_bus.deployment_status_updater.send_deployment_message")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
async def test_a_message_that_cannot_be_built_fails_the_step(update_mock, send_mock, updater):
    update_mock.side_effect = Exception("template not found")

    await updater.resend_pending_dispatch(pending_document())

    send_mock.assert_not_awaited()
    operation = updater.operations_repo.update_item.await_args.args[0]
    assert operation.steps[0].status == Status.DeploymentFailed
    assert "template not found" in operation.steps[0].message


@patch("service_bus.deployment_status_updater.asyncio.sleep", AsyncMock(side_effect=asyncio.CancelledError))
async def test_a_failed_entry_does_not_stop_the_pass(updater):
    first, second = pending_document(), pending_document()
    second["id"] = "second"
    updater.operations_repo.get_operations_with_pending_dispatch.return_value = [first, second]
    sent = []

    async def resend(document):
        if document is first:
            raise Exception("Service Bus is not available")
        sent.append(document["id"])

    updater.resend_pending_dispatch = resend
    with pytest.raises(asyncio.CancelledError):
        await updater.resend_pending_dispatches()

    assert sent == ["second"]
