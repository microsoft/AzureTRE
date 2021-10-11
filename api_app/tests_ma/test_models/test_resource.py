import pytest

from models.domain.request_action import RequestAction
from models.domain.resource import Resource, ResourceType
from models.domain.user_resource import UserResource
from models.domain.workspace_service import WorkspaceService


@pytest.mark.parametrize('resource, expected', [
    # enabled = True
    (Resource(resourceTemplateName="", resourceTemplateVersion="", resourceTemplateParameters={"enabled": True}, id="1234", resourceType=ResourceType.Workspace), True),
    # enabled = False
    (Resource(resourceTemplateName="", resourceTemplateVersion="", resourceTemplateParameters={"enabled": False}, id="1234", resourceType=ResourceType.Workspace), False),
    # enabled not set - defaults to True
    (Resource(resourceTemplateName="", resourceTemplateVersion="", resourceTemplateParameters={}, id="1234", resourceType=ResourceType.Workspace), True),
])
def test_resource_is_enabled_returns_correct_value(resource, expected):
    assert resource.is_enabled() == expected


def test_user_resource_get_resource_request_message_payload_augments_payload_with_extra_params():
    owner_id = "abc"
    workspace_id = "123"
    parent_service_id = "abcdef"

    user_resource = UserResource(id="123", resourceTemplateName="user-template", resourceTemplateVersion="1.0", ownerId=owner_id, workspaceId=workspace_id, parentWorkspaceServiceId=parent_service_id)

    message_payload = user_resource.get_resource_request_message_payload(RequestAction.Install)

    assert message_payload["workspaceId"] == workspace_id
    assert message_payload["ownerId"] == owner_id
    assert message_payload["parentWorkspaceServiceId"] == parent_service_id


def test_workspace_service_get_resource_request_message_payload_augments_payload_with_extra_params():
    workspace_id = "123"
    workspace_service = WorkspaceService(id="123", resourceTemplateName="service-template", resourceTemplateVersion="1.0", workspaceId=workspace_id)

    message_payload = workspace_service.get_resource_request_message_payload(RequestAction.Install)

    assert message_payload["workspaceId"] == workspace_id
