import pytest

from models.domain.request_action import RequestAction
from models.domain.resource import Resource, ResourceType
from models.domain.user_resource import UserResource
from models.domain.workspace_service import WorkspaceService


OPERATION_ID = "0000c8e7-5c42-4fcb-a7fd-294cfc27aa76"
STEP_ID = "main"


@pytest.mark.parametrize('resource, expected', [
    # enabled = True
    (Resource(templateName="", templateVersion="", isEnabled=True, etag="", properties={}, id="1234", resourceType=ResourceType.Workspace, resourcePath="test"), True),
    # enabled = False
    (Resource(templateName="", templateVersion="", isEnabled=False, etag="", properties={}, id="1234", resourceType=ResourceType.Workspace, resourcePath="test"), False),
    # enabled not set - defaults to True
    (Resource(templateName="", templateVersion="", properties={}, id="1234", etag="", resourceType=ResourceType.Workspace, resourcePath="test"), True),
])
def test_resource_is_enabled_returns_correct_value(resource, expected):
    assert resource.isEnabled == expected


def test_user_resource_get_resource_request_message_payload_augments_payload_with_extra_params():
    owner_id = "abc"
    workspace_id = "123"
    parent_service_id = "abcdef"

    user_resource = UserResource(id="123", templateName="user-template", templateVersion="1.0", etag="", ownerId=owner_id, workspaceId=workspace_id, parentWorkspaceServiceId=parent_service_id, resourcePath="test")

    message_payload = user_resource.get_resource_request_message_payload(OPERATION_ID, STEP_ID, RequestAction.Install)

    assert message_payload["workspaceId"] == workspace_id
    assert message_payload["ownerId"] == owner_id
    assert message_payload["parentWorkspaceServiceId"] == parent_service_id


def test_workspace_service_get_resource_request_message_payload_augments_payload_with_extra_params():
    workspace_id = "123"
    workspace_service = WorkspaceService(id="123", templateName="service-template", templateVersion="1.0", etag="", workspaceId=workspace_id, resourcePath="test")

    message_payload = workspace_service.get_resource_request_message_payload(OPERATION_ID, STEP_ID, RequestAction.Install)

    assert message_payload["workspaceId"] == workspace_id
