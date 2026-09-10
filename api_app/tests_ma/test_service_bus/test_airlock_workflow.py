import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
import pytest

from db.errors import EntityDoesNotExist
from models.domain.authentication import User
from models.domain.airlock_request import AirlockRequest, AirlockRedeployWorkflow, AirlockRequestType, AirlockReview, AirlockReviewDecision, AirlockReviewUserResource
from service_bus.airlock_workflow import AirlockWorkflowUpdater


@pytest.fixture
def updater():
    workflow = AirlockWorkflowUpdater()
    workflow.user_resource_repo = MagicMock()
    workflow.workspace_service_repo = MagicMock()
    workflow.operations_repo = MagicMock()
    workflow.resource_template_repo = MagicMock()
    workflow.resource_history_repo = MagicMock()
    workflow.airlock_request_repo = MagicMock()
    workflow.workspace_repo = MagicMock()
    workflow.airlock_request_repo.get_airlock_request_by_id = AsyncMock(return_value=AirlockRequest(
        id="request-id",
        workspaceId="workspace-id",
        type=AirlockRequestType.Import,
        createdBy=User.model_validate(user_payload()),
        reviewUserResources={"user-id": AirlockReviewUserResource(
            workspaceId="review-workspace-id",
            workspaceServiceId="service-id",
            userResourceId="resource-id")}
    ))
    workflow.workspace_repo.get_workspace_by_id = AsyncMock(return_value=MagicMock(properties={
        "airlock_review_config": {"import": {
            "import_vm_workspace_id": "review-workspace-id",
            "import_vm_workspace_service_id": "service-id",
            "import_vm_user_resource_template_name": "template"}}
    }))
    return workflow


def message(payload):
    return json.dumps(payload)


def user_payload():
    return User(id="user-id", name="Test User", email="test@example.com").model_dump()


@pytest.mark.asyncio
async def test_process_message_completes_cleanup_when_resource_is_already_deleted(updater):
    updater.user_resource_repo.get_user_resource_by_id = AsyncMock(side_effect=EntityDoesNotExist)

    result = await updater.process_message(message({
        "workflow": "cleanup",
        "airlock_request_id": "request-id",
        "review_user_id": "user-id",
    }))

    assert result is True
    updater.workspace_repo.get_workspace_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_message_reschedules_workspace_lease_contention(updater):
    updater.user_resource_repo.get_user_resource_by_id = AsyncMock(return_value=MagicMock(user=user_payload()))
    updater.workspace_service_repo.get_workspace_service_by_id = AsyncMock()
    lease_error = HTTPException(status_code=409, detail="Workspace has an active operation in progress")

    with patch("service_bus.airlock_workflow.disable_user_resource", new=AsyncMock(side_effect=lease_error)), \
            patch("service_bus.airlock_workflow.send_airlock_workflow_message", new=AsyncMock()) as schedule:
        result = await updater.process_message(message({
            "workflow": "cleanup",
            "airlock_request_id": "request-id",
            "review_user_id": "user-id",
        }))

    assert result is True
    schedule.assert_awaited_once()
    assert schedule.await_args.kwargs["delay_seconds"] == 30
    assert schedule.await_args.args[0]["lease_contention_retry_count"] == 1


@pytest.mark.asyncio
async def test_process_message_redeploys_without_duplicate_uninstall(updater):
    updater.user_resource_repo.get_user_resource_by_id = AsyncMock(side_effect=EntityDoesNotExist)

    payload = {
        "workflow": "redeploy",
        "airlock_request_id": "request-id",
        "operation_id": "delete-operation-id",
        "uninstall_started": True,
        "redeploy_workflow_id": "request-id:user-id:delete-operation-id",
    }

    with patch("service_bus.airlock_workflow.wait_for_successful_operation", new=AsyncMock()), \
            patch("service_bus.airlock_workflow.send_uninstall_message", new=AsyncMock()) as uninstall, \
            patch("service_bus.airlock_workflow._deploy_vm", new=AsyncMock(return_value=(MagicMock(id="new-resource-id"), MagicMock()))), \
            patch("service_bus.airlock_workflow.update_and_publish_event_airlock_request", new=AsyncMock()):
        result = await updater.process_message(message(payload))

    assert result is True
    uninstall.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_message_redeploys_legacy_resource_using_review_data(updater):
    workflow_id = "request-id:user-id:delete-operation-id"
    updater.user_resource_repo.get_user_resource_by_id = AsyncMock(side_effect=EntityDoesNotExist)
    updater.user_resource_repo.get_user_resource_by_workflow_id = AsyncMock(
        return_value=MagicMock(id="replacement-resource-id"))
    updater.airlock_request_repo.get_airlock_request_by_id = AsyncMock(return_value=AirlockRequest(
        id="request-id",
        workspaceId="workspace-id",
        type=AirlockRequestType.Import,
        createdBy=User(id="requester-id", name="Requester", email="requester@example.com").model_dump(),
        reviews=[AirlockReview(
            id="review-id",
            reviewDecision=AirlockReviewDecision.Approved,
            reviewer=User.model_validate(user_payload()))],
        reviewUserResources={"user-id": AirlockReviewUserResource(
            workspaceId="review-workspace-id",
            workspaceServiceId="service-id",
            userResourceId="resource-id")}
    ))

    payload = {
        "workflow": "redeploy",
        "redeploy_workflow_id": workflow_id,
        "airlock_request_id": "request-id",
        "operation_id": "delete-operation-id",
        "uninstall_started": True,
    }

    with patch("service_bus.airlock_workflow.wait_for_successful_operation", new=AsyncMock()), \
            patch("service_bus.airlock_workflow._deploy_vm", new=AsyncMock(return_value=(MagicMock(id="new-resource-id"), MagicMock()))), \
            patch("service_bus.airlock_workflow.update_and_publish_event_airlock_request", new=AsyncMock()):
        result = await updater.process_message(message(payload))

    assert result is True


@pytest.mark.asyncio
async def test_process_message_acknowledges_unknown_workflow_without_side_effects(updater):
    with patch("service_bus.airlock_workflow.wait_for_successful_operation", new=AsyncMock()) as wait_for_operation, \
            patch("service_bus.airlock_workflow.send_uninstall_message", new=AsyncMock()) as uninstall:
        result = await updater.process_message(message({
            "workflow": "future-workflow",
            "airlock_request_id": "request-id",
        }))

    assert result is True
    updater.user_resource_repo.get_user_resource_by_id.assert_not_called()
    wait_for_operation.assert_not_awaited()
    uninstall.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_message_rejects_forged_review_user_context(updater):
    with patch("service_bus.airlock_workflow.wait_for_successful_operation", new=AsyncMock()), \
            patch("service_bus.airlock_workflow.send_uninstall_message", new=AsyncMock()), \
            patch("service_bus.airlock_workflow._deploy_vm", new=AsyncMock()), \
            patch("service_bus.airlock_workflow.update_and_publish_event_airlock_request", new=AsyncMock()):
        result = await updater.process_message(message({
            "workflow": "cleanup",
            "airlock_request_id": "request-id",
            "review_user_id": "attacker-id",
            "user": user_payload(),
            "review_workspace_id": "attacker-workspace-id",
            "review_workspace_service_id": "attacker-service-id",
            "user_resource_id": "attacker-resource-id",
        }))

    assert result is False
    updater.user_resource_repo.get_user_resource_by_id.assert_not_called()


@pytest.mark.asyncio
async def test_process_message_recovers_deploying_redeploy_without_deploying_again(updater):
    workflow_id = "request-id:user-id"
    updater.user_resource_repo.get_user_resource_by_id = AsyncMock(
        side_effect=[EntityDoesNotExist, MagicMock(id="replacement-resource-id")])
    updater.operations_repo.get_operation_by_id = AsyncMock(
        return_value=MagicMock(status="deploying", resourceId="replacement-resource-id"))
    updater.airlock_request_repo.get_airlock_request_by_id = AsyncMock(return_value=AirlockRequest(
        id="request-id",
        workspaceId="workspace-id",
        type=AirlockRequestType.Import,
        createdBy=User.model_validate(user_payload()),
        reviewUserResources={"user-id": AirlockReviewUserResource(
            workspaceId="review-workspace-id",
            workspaceServiceId="service-id",
            userResourceId="resource-id")},
        redeployWorkflows={workflow_id: AirlockRedeployWorkflow(
            workflowId=workflow_id,
            phase="deploying",
            operationId="replacement-operation-id")}
    ))
    updater.workspace_repo.get_workspace_by_id = AsyncMock(return_value=MagicMock(properties={
        "airlock_review_config": {"import": {
            "import_vm_workspace_id": "review-workspace-id",
            "import_vm_workspace_service_id": "service-id",
            "import_vm_user_resource_template_name": "template"}}
    }))

    payload = {
        "workflow": "redeploy",
        "redeploy_workflow_id": workflow_id,
        "airlock_request_id": "request-id",
        "operation_id": "delete-operation-id",
        "uninstall_started": True,
    }

    with patch("service_bus.airlock_workflow.wait_for_successful_operation", new=AsyncMock()), \
            patch("service_bus.airlock_workflow._deploy_vm", new=AsyncMock()) as deploy, \
            patch("service_bus.airlock_workflow.update_and_publish_event_airlock_request", new=AsyncMock()) as update:
        result = await updater.process_message(message(payload))

    assert result is True
    deploy.assert_not_awaited()
    assert update.await_args.kwargs["redeploy_workflow"].phase == "completed"
    assert update.await_args.kwargs["redeploy_workflow"].operationId == "replacement-operation-id"


@pytest.mark.asyncio
async def test_process_message_acknowledges_invalid_message(updater):
    result = await updater.process_message("not-json")

    assert result is True
