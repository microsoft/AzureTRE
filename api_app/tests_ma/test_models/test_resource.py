import pytest
from pydantic import ValidationError

from models.domain.request_action import RequestAction
from models.domain.airlock_request import AirlockRequest, AirlockRequestType
from models.domain.operation import Operation, Status
from models.domain.restricted_resource import RestrictedProperties, RestrictedResource
from models.domain.resource import Output, Resource, ResourceHistoryItem, ResourceType
from models.domain.user_resource import UserResource
from models.domain.workspace_service import WorkspaceService
from models.schemas.resource import ResourceHistoryInList
from models.schemas.shared_service_template import SharedServiceTemplateInCreate
from models.schemas.user_resource_template import UserResourceTemplateInCreate
from models.schemas.workspace_service_template import WorkspaceServiceTemplateInCreate
from models.schemas.workspace_template import WorkspaceTemplateInCreate


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


def test_legacy_actor_dicts_validate_without_user_required_fields():
    resource = Resource.model_validate({
        "id": "resource-id",
        "templateName": "workspace",
        "templateVersion": "1.0",
        "properties": {},
        "resourceType": ResourceType.Workspace,
        "_etag": "etag",
        "user": {"id": "legacy-user"},
    })
    operation = Operation.model_validate({
        "id": "operation-id",
        "resourceId": "resource-id",
        "resourcePath": "/workspaces/resource-id",
        "status": Status.AwaitingDeployment,
        "action": "install",
        "user": {},
    })
    airlock_request = AirlockRequest.model_validate({
        "id": "airlock-id",
        "workspaceId": "workspace-id",
        "type": AirlockRequestType.Import,
        "createdBy": {},
        "updatedBy": {"name": "Legacy User"},
    })

    assert resource.user == {"id": "legacy-user"}
    assert operation.user == {}
    assert airlock_request.createdBy == {}
    assert airlock_request.updatedBy == {"name": "Legacy User"}
    assert airlock_request.createdWhen is None
    assert isinstance(airlock_request.updatedWhen, float)


def test_restricted_resource_optional_fields_default_to_none():
    restricted_resource = RestrictedResource(
        id="resource-id",
        templateName="workspace",
        templateVersion="1.0",
        resourceType=ResourceType.Workspace,
        _etag="etag",
    )

    assert isinstance(restricted_resource.properties, RestrictedProperties)
    assert isinstance(restricted_resource.updatedWhen, float)
    assert restricted_resource.availableUpgrades is None
    assert restricted_resource.deploymentStatus is None


def test_resource_omitted_timestamps_use_float_defaults():
    resource_history = ResourceHistoryItem(id="history-id", resourceId="resource-id")
    resource = Resource(
        id="resource-id",
        templateName="workspace",
        templateVersion="1.0",
        resourceType=ResourceType.Workspace,
        _etag="etag",
    )

    assert isinstance(resource_history.updatedWhen, float)
    assert isinstance(resource.updatedWhen, float)


def test_output_requires_value():
    with pytest.raises(ValidationError):
        Output(name="output-name", type="string")


def test_resource_history_example_uses_declared_field_types():
    example = ResourceHistoryInList.model_config["json_schema_extra"]["example"]
    resource_history = ResourceHistoryInList.model_validate(example).resource_history[0]

    assert isinstance(resource_history.isEnabled, bool)
    assert isinstance(resource_history.resourceVersion, int)
    assert isinstance(resource_history.updatedWhen, float)
    assert isinstance(resource_history.user, dict)


@pytest.mark.parametrize("model", [
    SharedServiceTemplateInCreate,
    UserResourceTemplateInCreate,
    WorkspaceServiceTemplateInCreate,
    WorkspaceTemplateInCreate,
])
def test_resource_template_create_examples_use_boolean_current(model):
    example = model.model_config["json_schema_extra"]["example"]
    template = model.model_validate(example)

    assert isinstance(example["current"], bool)
    assert isinstance(template.current, bool)
