import pytest

from models.domain.resource_template import ResourceTemplate, ResourceType
from models.domain.user_resource_template import UserResourceTemplate
from models.schemas.user_resource_template import UserResourceTemplateInCreate, UserResourceTemplateInResponse
from models.schemas.workspace_template import WorkspaceTemplateInCreate
from models.schemas.workspace_service_template import WorkspaceServiceTemplateInCreate


@pytest.fixture
def input_workspace_template():
    return WorkspaceTemplateInCreate(
        name="my-tre-workspace",
        version="0.0.1",
        current=True,
        json_schema={
            "$schema": "http://json-schema.org/draft-07/schema",
            "$id": "https://github.com/microsoft/AzureTRE/templates/workspaces/myworkspace/workspace.json",
            "type": "object",
            "title": "My Workspace Template",
            "description": "This is a test workspace template schema.",
            "required": [],
            "properties": {}
        },
        customActions=[
            {
                "name": "my-custom-action",
                "description": "This is a test custom action"
            }
        ])


@pytest.fixture
def input_workspace_service_template():
    return WorkspaceServiceTemplateInCreate(
        name="my-tre-workspace-service",
        version="0.0.1",
        current=True,
        json_schema={
            "$schema": "http://json-schema.org/draft-07/schema",
            "$id": "https://github.com/microsoft/AzureTRE/templates/workspaces/myworkspace/workspace_service.json",
            "type": "object",
            "title": "My Workspace Service Template",
            "description": "This is a test workspace service template schema.",
            "required": [],
            "properties": {}
        },
        customActions=[
            {
                "name": "my-custom-action",
                "description": "This is a test custom action"
            }
        ])


@pytest.fixture
def input_user_resource_template():
    return UserResourceTemplateInCreate(
        name="my-tre-user-resource",
        version="0.0.1",
        current=True,
        json_schema={
            "$schema": "http://json-schema.org/draft-07/schema",
            "$id": "https://github.com/microsoft/AzureTRE/templates/workspaces/myworkspace/user_resource.json",
            "type": "object",
            "title": "My User Resource Template",
            "description": "These is a test user resource template schema",
            "required": [],
            "properties": {}
        },
        customActions=[
            {
                "name": "my-custom-action",
                "description": "This is a test custom action"
            }
        ])


@pytest.fixture
def basic_resource_template(input_workspace_template):
    return ResourceTemplate(
        id="1234-5678",
        name=input_workspace_template.name,
        description=input_workspace_template.json_schema["description"],
        version=input_workspace_template.name,
        resourceType=ResourceType.Workspace,
        current=True,
        required=input_workspace_template.json_schema["required"],
        properties=input_workspace_template.json_schema["properties"],
        actions=input_workspace_template.customActions
    )


@pytest.fixture
def basic_workspace_service_template(input_workspace_template):
    return ResourceTemplate(
        id="1234-5678",
        name=input_workspace_template.name,
        description=input_workspace_template.json_schema["description"],
        version=input_workspace_template.name,
        resourceType=ResourceType.WorkspaceService,
        current=True,
        required=input_workspace_template.json_schema["required"],
        properties=input_workspace_template.json_schema["properties"],
        actions=input_workspace_template.customActions

    )


@pytest.fixture
def basic_user_resource_template(input_user_resource_template):
    return UserResourceTemplate(
        id="1234-5678",
        name=input_user_resource_template.name,
        parentWorkspaceService="parent-workspace-service-name",
        description=input_user_resource_template.json_schema["description"],
        version=input_user_resource_template.version,
        resourceType=ResourceType.UserResource,
        current=True,
        required=input_user_resource_template.json_schema["required"],
        properties=input_user_resource_template.json_schema["properties"],
        actions=input_user_resource_template.customActions
    )


@pytest.fixture
def user_resource_template_in_response(input_user_resource_template):
    return UserResourceTemplateInResponse(
        id="1234-5678",
        name=input_user_resource_template.name,
        parentWorkspaceService="parent-workspace-service-name",
        description=input_user_resource_template.json_schema["description"],
        version=input_user_resource_template.version,
        resourceType=ResourceType.UserResource,
        current=True,
        required=input_user_resource_template.json_schema["required"],
        properties=input_user_resource_template.json_schema["properties"],
        actions=input_user_resource_template.customActions,
        system_properties={}
    )
