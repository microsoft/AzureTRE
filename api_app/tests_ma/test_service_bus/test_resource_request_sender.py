import json
import pytest
import uuid

from azure.servicebus import ServiceBusMessage
from mock import AsyncMock, patch
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
@patch('service_bus.resource_request_sender.ServiceBusClient')
async def test_resource_request_message_generated_correctly(service_bus_client_mock, operations_repo_mock, request_action):
    service_bus_client_mock().get_queue_sender().send_messages = AsyncMock()
    resource = create_test_resource()

    operations_repo_mock.create_operation_item.return_value = create_sample_operation(resource.id)

    await send_resource_request_message(resource, operations_repo_mock, request_action)

    args = service_bus_client_mock().get_queue_sender().send_messages.call_args.args
    assert len(args) == 1
    assert isinstance(args[0], ServiceBusMessage)

    sent_message = args[0]
    assert sent_message.correlation_id == resource.id
    sent_message_as_json = json.loads(str(sent_message))
    assert sent_message_as_json["id"] == resource.id
    assert sent_message_as_json["action"] == request_action
