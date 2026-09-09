import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.errors import EntityDoesNotExist
from models.domain.authentication import User
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
        "user": user_payload(),
        "review_workspace_id": "workspace-id",
        "review_workspace_service_id": "service-id",
        "user_resource_id": "resource-id",
    }))

    assert result is True


@pytest.mark.asyncio
async def test_process_message_redeploys_without_duplicate_uninstall(updater):
    updater.user_resource_repo.get_user_resource_by_id = AsyncMock(side_effect=EntityDoesNotExist)
    updater.operations_repo.get_operation_by_id = AsyncMock()
    updater.airlock_request_repo.get_airlock_request_by_id = AsyncMock()
    updater.workspace_repo.get_workspace_by_id = AsyncMock()

    payload = {
        "workflow": "redeploy",
        "user": user_payload(),
        "airlock_request_id": "request-id",
        "workspace_id": "workspace-id",
        "review_workspace_id": "review-workspace-id",
        "review_workspace_service_id": "service-id",
        "user_resource_template_name": "template",
        "user_resource_id": "resource-id",
        "operation_id": "delete-operation-id",
        "uninstall_started": True,
    }

    with patch("service_bus.airlock_workflow.wait_for_successful_operation", new=AsyncMock()), \
            patch("service_bus.airlock_workflow.send_uninstall_message", new=AsyncMock()) as uninstall, \
            patch("service_bus.airlock_workflow._deploy_vm", new=AsyncMock(return_value=(MagicMock(id="new-resource-id"), MagicMock()))), \
            patch("service_bus.airlock_workflow.update_and_publish_event_airlock_request", new=AsyncMock()):
        result = await updater.process_message(message(payload))

    assert result is True
    uninstall.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_message_acknowledges_invalid_message(updater):
    result = await updater.process_message("not-json")

    assert result is True
