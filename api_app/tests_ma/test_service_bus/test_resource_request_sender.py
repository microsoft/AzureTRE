import json
import pytest
import uuid

from azure.servicebus import ServiceBusMessage
from mock import AsyncMock, patch
from models.schemas.workspace_template import get_sample_workspace_template_object
from tests_ma.test_api.conftest import create_test_user
from tests_ma.test_service_bus.test_deployment_status_update import create_sample_operation

from models.domain.resource import Resource, ResourceType
from service_bus.resource_request_sender import send_resource_request_message, RequestAction


pytestmark = pytest.mark.asyncio


def create_test_resource():
    return Resource(
        id=str(uuid.uuid4()),
        resourceType=ResourceType.Workspace,
        templateName="Test resource template name",
        templateVersion="2.718",
        etag='',
        properties={"testParameter": "testValue"},
        resourcePath="test"
    )


@pytest.mark.parametrize('request_action', [RequestAction.Install, RequestAction.UnInstall])
@patch('service_bus.resource_request_sender.OperationRepository')
@patch('service_bus.step_helpers.ServiceBusClient')
@patch('service_bus.resource_request_sender.ResourceRepository')
@patch('service_bus.resource_request_sender.ResourceTemplateRepository')
async def test_resource_request_message_generated_correctly(resource_template_repo, resource_repo, service_bus_client_mock, operations_repo_mock, request_action):
    service_bus_client_mock().get_queue_sender().send_messages = AsyncMock()
    resource = create_test_resource()
    operation = create_sample_operation(resource.id, request_action)
    template = get_sample_workspace_template_object()
    operations_repo_mock.create_operation_item.return_value = operation
    resource_repo.get_resource_by_id.return_value = resource

    await send_resource_request_message(
        resource=resource,
        operations_repo=operations_repo_mock,
        resource_repo=resource_repo,
        user=create_test_user(),
        resource_template=template,
        resource_template_repo=resource_template_repo,
        action=request_action)

    args = service_bus_client_mock().get_queue_sender().send_messages.call_args.args
    assert len(args) == 1
    assert isinstance(args[0], ServiceBusMessage)

    sent_message = args[0]
    assert sent_message.correlation_id == operation.id
    sent_message_as_json = json.loads(str(sent_message))
    assert sent_message_as_json["id"] == resource.id
    assert sent_message_as_json["action"] == request_action
