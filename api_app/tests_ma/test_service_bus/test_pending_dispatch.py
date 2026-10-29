import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

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
MESSAGE_ID = f"{OPERATION_ID}:random-uuid"
AWAITING = {"upgrade": Status.AwaitingUpdate, "uninstall": Status.AwaitingDeletion, "start": Status.AwaitingAction}


def pending_document(action="install", status=Status.AwaitingDeployment):
    operation = create_sample_operation(RESOURCE_ID, action)
    operation.steps[0].status = status
    document = operation.model_dump()
    document["_etag"] = "etag"
    document[PENDING_DISPATCH] = {"stepId": "random-uuid", "messageId": MESSAGE_ID, "createdWhen": 1.0}
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
    updater.operations_repo.get_operations_by_resource_id.return_value = []
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


@patch("service_bus.deployment_status_updater.send_deployment_message")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
async def test_sensitive_values_of_an_install_fail_the_step(update_mock, send_mock, updater):
    update_mock.return_value = workspace({"settings": {"secret": strings.REDACTED_SENSITIVE_VALUE}})

    await updater.resend_pending_dispatch(pending_document())

    send_mock.assert_not_awaited()
    operation = updater.operations_repo.update_item.await_args.args[0]
    assert operation.steps[0].status == Status.DeploymentFailed
    assert operation.steps[0].message == NOT_SENT_WITH_SENSITIVE_VALUES
    assert operation.status == Status.DeploymentFailed
    assert updater.resource_repo.update_item.await_args.args[0].deploymentStatus == Status.DeploymentFailed


@pytest.mark.parametrize("action", ["upgrade", "uninstall", "start"])
@patch("service_bus.deployment_status_updater.send_deployment_message")
@patch("service_bus.deployment_status_updater.update_resource_for_step")
async def test_other_requests_send_the_placeholder_as_the_first_send_did(update_mock, send_mock, updater, action):
    # The API builds these requests from Cosmos DB, so the first send also had the placeholder.
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
    updater.operations_repo.get_operations_by_resource_id.return_value = [later]

    await updater.resend_pending_dispatch(document)

    update_mock.assert_not_awaited()
    send_mock.assert_not_awaited()
    operation = updater.operations_repo.update_item.await_args.args[0]
    assert operation.steps[0].status == Status.DeploymentFailed
    assert operation.steps[0].message == NOT_SENT_BEFORE_A_LATER_REQUEST


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
