
import json
import pytest
import uuid

from azure.servicebus import ServiceBusMessage
from mock import AsyncMock, patch
from resources import strings
from models.schemas.resource import ResourcePatch
from service_bus.helpers import (
    try_update_with_retries,
    update_resource_for_step,
)
from tests_ma.test_api.conftest import create_test_user
from tests_ma.test_service_bus.test_deployment_status_update import (
    create_sample_operation,
)
from models.domain.workspace_service import WorkspaceService
from models.domain.resource import Resource, ResourceType
from service_bus.resource_request_sender import (
    send_resource_request_message,
    RequestAction,
)
from azure.cosmos.exceptions import CosmosAccessConditionFailedError

pytestmark = pytest.mark.asyncio


def create_test_resource():
    return Resource(
        id=str(uuid.uuid4()),
        resourceType=ResourceType.Workspace,
        templateName="Test resource template name",
        templateVersion="2.718",
        etag="",
        properties={"testParameter": "testValue"},
        resourcePath="test",
    )


@pytest.mark.parametrize(
    "request_action", [RequestAction.Install, RequestAction.UnInstall]
)
@patch("service_bus.resource_request_sender.ResourceHistoryRepository.create")
@patch("service_bus.resource_request_sender.OperationRepository.create")
@patch("service_bus.helpers.ServiceBusClient")
@patch("service_bus.resource_request_sender.ResourceRepository.create")
@patch("service_bus.resource_request_sender.ResourceTemplateRepository.create")
async def test_resource_request_message_generated_correctly(
    resource_template_repo,
    resource_repo,
    service_bus_client_mock,
    operations_repo_mock,
    resource_history_repo_mock,
    request_action,
    multi_step_resource_template
):
    service_bus_client_mock().get_queue_sender().send_messages = AsyncMock()
    resource = create_test_resource()
    operation = create_sample_operation(resource.id, request_action)
    operations_repo_mock.create_operation_item.return_value = operation
    resource_repo.get_resource_by_id.return_value = resource
    resource_template_repo.get_template_by_name_and_version.return_value = multi_step_resource_template

    resource_repo.patch_resource.return_value = (resource, multi_step_resource_template)

    await send_resource_request_message(
        resource=resource,
        operations_repo=operations_repo_mock,
        resource_repo=resource_repo,
        user=create_test_user(),
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo_mock,
        action=request_action
    )

    args = service_bus_client_mock().get_queue_sender().send_messages.call_args.args
    assert len(args) == 1
    assert isinstance(args[0], ServiceBusMessage)

    sent_message = args[0]
    assert sent_message.correlation_id == operation.id
    sent_message_as_json = json.loads(str(sent_message))
    assert sent_message_as_json["id"] == resource.id
    assert sent_message_as_json["action"] == request_action


@patch("service_bus.resource_request_sender.ResourceHistoryRepository.create")
@patch("service_bus.resource_request_sender.OperationRepository.create")
@patch("service_bus.resource_request_sender.ResourceRepository.create")
@patch("service_bus.resource_request_sender.ResourceTemplateRepository.create")
async def test_multi_step_document_sends_first_step(
    resource_template_repo,
    resource_repo,
    operations_repo_mock,
    resource_history_repo_mock,
    multi_step_operation,
    basic_shared_service,
    basic_shared_service_template,
    multi_step_resource_template,
    user_resource_multi,
    test_user,
):
    operations_repo_mock.return_value.create_operation_item.return_value = multi_step_operation
    temp_workspace_service = WorkspaceService(
        id="123", templateName="template-name-here", templateVersion="0.1.0", etag=""
    )

    # return the primary resource, a 'parent' workspace service, then the shared service to patch
    resource_repo.return_value.get_resource_by_id.side_effect = [
        user_resource_multi,
        temp_workspace_service,
        basic_shared_service,
    ]
    resource_template_repo.get_template_by_name_and_version.side_effect = [
        multi_step_resource_template,
        basic_shared_service_template,
    ]

    resource_repo.patch_resource.return_value = (basic_shared_service, basic_shared_service_template)

    resource_repo.get_resource_by_id.return_value = basic_shared_service

    _ = await update_resource_for_step(
        operation_step=multi_step_operation.steps[0],
        resource_repo=resource_repo,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo_mock,
        step_resource=user_resource_multi,
        root_resource=None,
        resource_to_update_id=basic_shared_service.id,
        primary_action=strings.RESOURCE_ACTION_INSTALL,
        user=test_user,
    )

    expected_patch = ResourcePatch(properties={"display_name": "new name"})

    # expect the patch for step 1
    resource_repo.patch_resource.assert_called_once_with(
        resource=basic_shared_service,
        resource_patch=expected_patch,
        resource_template=basic_shared_service_template,
        resource_history_repo=resource_history_repo_mock,
        etag=basic_shared_service.etag,
        resource_template_repo=resource_template_repo,
        user=test_user,
        resource_action=strings.RESOURCE_ACTION_UPDATE
    )


@patch("service_bus.resource_request_sender.ResourceHistoryRepository.create")
@patch("service_bus.resource_request_sender.ResourceRepository.create")
@patch("service_bus.resource_request_sender.ResourceTemplateRepository.create")
async def test_multi_step_document_retries(
    resource_template_repo,
    resource_repo,
    resource_history_repo,
    basic_shared_service,
    basic_shared_service_template,
    test_user,
    multi_step_resource_template,
    primary_resource
):

    resource_repo.get_resource_by_id.return_value = basic_shared_service
    resource_template_repo.get_current_template.return_value = (
        basic_shared_service_template
    )

    # simulate an etag mismatch
    resource_repo.patch_resource.side_effect = CosmosAccessConditionFailedError

    num_retries = 5
    try:
        await try_update_with_retries(
            num_retries=num_retries,
            attempt_count=0,
            resource_repo=resource_repo,
            resource_template_repo=resource_template_repo,
            user=test_user,
            resource_to_update_id="resource-id",
            template_step=multi_step_resource_template.pipeline.install[0],
            resource_history_repo=resource_history_repo,
            primary_resource=primary_resource,
            primary_parent_workspace=None,
            primary_parent_workspace_svc=None
        )
    except CosmosAccessConditionFailedError:
        pass

    # check it tried to patch and re-get the item the first time + all the retries
    assert len(resource_repo.patch_resource.mock_calls) == (num_retries + 1)
    assert len(resource_repo.get_resource_by_id.mock_calls) == (num_retries + 1)
