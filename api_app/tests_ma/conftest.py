import pytest
import pytest_asyncio
from mock import patch
from models.domain.request_action import RequestAction
from models.domain.resource import Resource
from models.domain.user_resource import UserResource
from models.domain.shared_service import SharedService
from tests_ma.test_api.test_routes.test_resource_helpers import FAKE_CREATE_TIMESTAMP
from models.domain.authentication import User
from models.domain.operation import Operation, OperationStep, Status

from models.domain.resource_template import (
    Pipeline,
    PipelineStep,
    PipelineStepProperty,
    ResourceTemplate,
    ResourceType,
)
from models.domain.user_resource_template import UserResourceTemplate
from models.schemas.user_resource_template import (
    UserResourceTemplateInCreate,
    UserResourceTemplateInResponse,
)
from models.schemas.workspace_template import WorkspaceTemplateInCreate
from models.schemas.workspace_service_template import WorkspaceServiceTemplateInCreate
from models.schemas.shared_service_template import SharedServiceTemplateInCreate


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
            "properties": {
                "updateable_property": {
                    "type": "string",
                    "title": "Test updateable property",
                    "updateable": True,
                },
                "fixed_property": {
                    "type": "string",
                    "title": "Test fixed property",
                    "updateable": False,
                },
                "supply_secret": {
                    "type": "boolean",
                    "title": "Choose to supply a secret",
                    "updateable": True,
                },
                "prop_with_nested_secret": {
                    "type": "object",
                    "title": "Property containing a nested secret val",
                    "properties": {
                        "nested_secret": {
                            "type": "string",
                            "title": "Nested Secret",
                            "sensitive": True,
                        }
                    },
                },
            },
            "allOf": [
                {
                    "if": {
                        "properties": {"supply_secret": {"const": True}},
                        "required": ["supply_secret"],
                    },
                    "then": {
                        "properties": {
                            "secret": {
                                "type": "string",
                                "title": "Secret",
                                "sensitive": True,
                            }
                        }
                    },
                }
            ],
        },
        customActions=[
            {"name": "my-custom-action", "description": "This is a test custom action"}
        ],
    )


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
            "properties": {},
        },
        customActions=[
            {"name": "my-custom-action", "description": "This is a test custom action"}
        ],
    )


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
            "properties": {},
        },
        customActions=[
            {"name": "my-custom-action", "description": "This is a test custom action"}
        ],
    )


@pytest.fixture
def input_shared_service_template():
    return SharedServiceTemplateInCreate(
        name="my-tre-shared-service",
        version="0.0.1",
        current=True,
        json_schema={
            "$schema": "http://json-schema.org/draft-07/schema",
            "$id": "https://github.com/microsoft/AzureTRE/templates/shared_services/mysharedservice/shared_service.json",
            "type": "object",
            "title": "My Shared Service Template",
            "description": "This is a test shared service template schema.",
            "required": [],
            "properties": {},
        },
    )


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
        authorizedRoles=input_workspace_template.json_schema["authorizedRoles"]
        if "authorizedRoles" in input_workspace_template.json_schema
        else [],
        properties=input_workspace_template.json_schema["properties"],
        allOf=input_workspace_template.json_schema["allOf"],
        customActions=input_workspace_template.customActions,
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
        authorizedRoles=input_workspace_template.json_schema["authorizedRoles"]
        if "authorizedRoles" in input_workspace_template.json_schema
        else [],
        properties=input_workspace_template.json_schema["properties"],
        customActions=input_workspace_template.customActions,
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
        authorizedRoles=input_user_resource_template.json_schema["authorizedRoles"]
        if "authorizedRoles" in input_user_resource_template.json_schema
        else [],
        properties=input_user_resource_template.json_schema["properties"],
        customActions=input_user_resource_template.customActions,
    )


@pytest.fixture
def basic_shared_service_template(input_shared_service_template):
    return ResourceTemplate(
        id="1234-5678",
        name=input_shared_service_template.name,
        description=input_shared_service_template.json_schema["description"],
        version=input_shared_service_template.name,
        resourceType=ResourceType.SharedService,
        current=True,
        required=input_shared_service_template.json_schema["required"],
        authorizedRoles=input_shared_service_template.json_schema["authorizedRoles"]
        if "authorizedRoles" in input_shared_service_template.json_schema
        else [],
        properties=input_shared_service_template.json_schema["properties"],
        actions=input_shared_service_template.customActions,
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
        authorizedRoles=input_user_resource_template.json_schema["authorizedRoles"]
        if "authorizedRoles" in input_user_resource_template.json_schema
        else [],
        properties=input_user_resource_template.json_schema["properties"],
        customActions=input_user_resource_template.customActions,
        system_properties={},
    )


@pytest.fixture
def multi_step_resource_template(basic_shared_service_template) -> ResourceTemplate:
    return ResourceTemplate(
        id="123",
        name="template1",
        description="description",
        version="0.1.0",
        resourceType=ResourceType.Workspace,
        current=True,
        required=[],
        properties={},
        customActions=[],
        pipeline=Pipeline(
            install=[
                PipelineStep(
                    stepId="pre-step-1",
                    stepTitle="Title for pre-step-1",
                    resourceTemplateName=basic_shared_service_template.name,
                    resourceType=basic_shared_service_template.resourceType,
                    resourceAction="upgrade",
                    properties=[
                        PipelineStepProperty(
                            name="display_name", type="string", value="new name"
                        )
                    ],
                ),
                PipelineStep(stepId="main"),
                PipelineStep(
                    stepId="post-step-1",
                    stepTitle="Title for post-step-1",
                    resourceTemplateName=basic_shared_service_template.name,
                    resourceType=basic_shared_service_template.resourceType,
                    resourceAction="upgrade",
                    properties=[
                        PipelineStepProperty(
                            name="display_name", type="string", value="old name"
                        )
                    ],
                ),
            ]
        ),
    )


@pytest.fixture
def test_user():
    return User(id="user-id", name="test user", email="test@user.com")


@pytest.fixture
def basic_shared_service(test_user, basic_shared_service_template):
    id = "59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76"
    return SharedService(
        id=id,
        templateName=basic_shared_service_template.name,
        templateVersion=basic_shared_service_template.version,
        etag="",
        properties={},
        resourcePath=f"/shared-services/{id}",
        updatedWhen=FAKE_CREATE_TIMESTAMP,
        user=test_user,
    )


@pytest.fixture
def user_resource_multi(test_user, multi_step_resource_template):
    id = "resource-id"
    return UserResource(
        id=id,
        templateName=multi_step_resource_template.name,
        templateVersion=multi_step_resource_template.version,
        etag="",
        properties={},
        resourcePath=f"/workspaces/foo/workspace-services/bar/user-resources/{id}",
        updatedWhen=FAKE_CREATE_TIMESTAMP,
        user=test_user,
    )


@pytest.fixture
def multi_step_operation(
    test_user, basic_shared_service_template, basic_shared_service
):
    return Operation(
        id="op-guid-here",
        resourceId="59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
        action=RequestAction.Install,
        user=test_user,
        resourcePath="/workspaces/59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
        createdWhen=FAKE_CREATE_TIMESTAMP,
        updatedWhen=FAKE_CREATE_TIMESTAMP,
        steps=[
            OperationStep(
                stepId="pre-step-1",
                stepTitle="Title for pre-step-1",
                resourceAction="upgrade",
                resourceTemplateName=basic_shared_service_template.name,
                resourceType=basic_shared_service_template.resourceType,
                resourceId=basic_shared_service.id,
                status=Status.AwaitingUpdate,
                message="This resource is waiting to be updated",
                updatedWhen=FAKE_CREATE_TIMESTAMP,
                parentResourceTemplate="template1",
                parentResourceTemplateVersion="0.1.0",
                parentResourceType=ResourceType.Workspace,
                parentResourceId="59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76"
            ),
            OperationStep(
                stepId="main",
                stepTitle="Main step for 59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
                resourceAction="install",
                resourceType=ResourceType.Workspace,
                resourceTemplateName="template1",
                resourceId="59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
                status=Status.AwaitingDeployment,
                message="This resource is waiting to be deployed",
                updatedWhen=FAKE_CREATE_TIMESTAMP,
                parentResourceTemplate='',
                parentResourceTemplateVersion='',
                parentResourceType=None,
                parentResourceId=None
            ),
            OperationStep(
                stepId="post-step-1",
                stepTitle="Title for post-step-1",
                resourceAction="upgrade",
                resourceType=basic_shared_service_template.resourceType,
                resourceTemplateName=basic_shared_service_template.name,
                resourceId=basic_shared_service.id,
                status=Status.AwaitingUpdate,
                message="This resource is waiting to be updated",
                updatedWhen=FAKE_CREATE_TIMESTAMP,
                parentResourceTemplate="template1",
                parentResourceTemplateVersion="0.1.0",
                parentResourceType=ResourceType.Workspace,
                parentResourceId="59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76"
            ),
        ],
    )


@pytest.fixture
def primary_resource() -> Resource:
    return Resource(
        id="123",
        name="test resource",
        isEnabled=True,
        templateName="template name",
        templateVersion="7",
        resourceType="workspace",
        _etag="",
        properties={
            "display_name": "test_resource name",
            "address_prefix": ["172.0.0.1", "192.168.0.1"],
            "fqdn": ["*pypi.org", "files.pythonhosted.org", "security.ubuntu.com"],
            "my_protocol": "MyCoolProtocol",
        },
    )


@pytest.fixture
def resource_to_update() -> Resource:
    return Resource(
        id="123",
        name="Firewall",
        isEnabled=True,
        templateName="template name",
        templateVersion="7",
        resourceType="workspace",
        _etag="",
        properties={},
    )


@pytest.fixture
def pipeline_step() -> PipelineStep:
    return PipelineStep(
        properties=[
            PipelineStepProperty(
                name="rule_collections",
                type="array",
                arraySubstitutionAction="overwrite",
                arrayMatchField="name",
                value={
                    "name": "arc-web_app_subnet_nexus_api",
                    "action": "Allow",
                    "rules": [
                        {
                            "name": "nexus-package-sources-api",
                            "description": "Deployed by {{ resource.id }}",
                            "protocols": [
                                {"port": "443", "type": "Https"},
                                {
                                    "port": "80",
                                    "type": "{{ resource.properties.my_protocol }}",
                                },
                            ],
                            "target_fqdns": "{{ resource.properties.fqdn }}",
                            "source_addresses": "{{ resource.properties.address_prefix }}",
                        }
                    ],
                },
            )
        ]
    )


@pytest.fixture
def simple_pipeline_step() -> PipelineStep:
    return PipelineStep(
        properties=[
            PipelineStepProperty(
                name="just_text", type="string", value="Updated by {{resource.id}}"
            ),
            PipelineStepProperty(
                name="just_text_2",
                type="string",
                value="No substitution, just a fixed string here",
            ),
            PipelineStepProperty(
                name="just_text_3",
                type="string",
                value="Multiple substitutions -> {{resource.id}} and {{resource.templateName}}",
            ),
        ]
    )


@pytest_asyncio.fixture()
def no_database():
    """ overrides connecting to the database """
    with patch('api.dependencies.database.connect_to_db', return_value=None):
        with patch('api.dependencies.database.get_db_client', return_value=None):
            with patch('db.repositories.base.BaseRepository._get_container', return_value=None):
                with patch('core.events.bootstrap_database', return_value=None):
                    yield
