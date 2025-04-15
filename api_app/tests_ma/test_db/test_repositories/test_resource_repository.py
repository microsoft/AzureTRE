import copy
from unittest.mock import AsyncMock
import uuid
import pytest
import pytest_asyncio
from mock import patch, MagicMock

from jsonschema.exceptions import ValidationError
from resources import strings
from db.repositories.resources_history import ResourceHistoryRepository
from tests_ma.test_api.test_routes.test_resource_helpers import FAKE_CREATE_TIMESTAMP, FAKE_UPDATE_TIMESTAMP
from tests_ma.test_api.conftest import create_test_user

from db.errors import EntityDoesNotExist, UserNotAuthorizedToUseTemplate
from db.repositories.resources import ResourceRepository
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from models.domain.resource import Resource
from models.domain.resource_template import ResourceTemplate
from models.domain.user_resource_template import UserResourceTemplate
from models.domain.workspace import ResourceType
from models.schemas.resource import ResourcePatch
from models.schemas.workspace import WorkspaceInCreate


RESOURCE_ID = str(uuid.uuid4())


@pytest_asyncio.fixture
async def resource_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=None):
        resource_repo = await ResourceRepository().create()
        yield resource_repo


@pytest_asyncio.fixture
async def resource_history_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=None):
        resource_history_repo = await ResourceHistoryRepository().create()
        yield resource_history_repo


@pytest.fixture
def workspace_input():
    return WorkspaceInCreate(templateName="base-tre", properties={"display_name": "test", "description": "test", "client_id": "123"})


def sample_resource() -> Resource:
    return Resource(
        id=RESOURCE_ID,
        isEnabled=True,
        resourcePath="/resource/path",
        templateName="template_name",
        templateVersion="template_version",
        properties={
            'display_name': 'initial display name',
            'description': 'initial description',
            'computed_prop': 'computed_val'
        },
        resourceType=ResourceType.Workspace,
        etag="some-etag-value",
        resourceVersion=0,
        updatedWhen=FAKE_CREATE_TIMESTAMP,
        user=create_test_user()
    )


def sample_resource_template() -> ResourceTemplate:
    return ResourceTemplate(id="123",
                            name="tre-user-resource",
                            description="description",
                            version="0.1.0",
                            resourceType=ResourceType.UserResource,
                            current=True,
                            required=['os_image', 'title'],
                            properties={
                                'title': {
                                    'type': 'string',
                                    'title': 'Title of the resource'
                                },
                                'os_image': {
                                    'type': 'string',
                                    'title': 'Windows image',
                                    'description': 'Select Windows image to use for VM',
                                    'enum': [
                                        'Windows 10',
                                        'Server 2019 Data Science VM'
                                    ],
                                    'updateable': False
                                },
                                'vm_size': {
                                    'type': 'string',
                                    'title': 'Windows image',
                                    'description': 'Select Windows image to use for VM',
                                    'enum': [
                                        'small',
                                        'large'
                                    ],
                                    'updateable': True
                                }
                            },
                            actions=[]).dict(exclude_none=True)


def sample_nested_template() -> ResourceTemplate:
    return ResourceTemplate(
        id="123",
        name="template1",
        description="description",
        version="0.1.0",
        resourceType=ResourceType.Workspace,
        current=True,
        required=[],
        properties={
            'rules': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'required': [],
                    'properties': {
                        'protocol': {
                            'type': 'object',
                            'required': ['port'],
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'port': {
                                        'type': 'string'
                                    },
                                    'method': {
                                        'type': 'string'
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        customActions=[]
    ).dict(exclude_none=True)


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
@patch("db.repositories.resources.ResourceRepository._validate_resource_parameters", return_value=None)
async def test_validate_input_against_template_returns_template_version_if_template_is_valid(_, enriched_template_mock, resource_repo, workspace_input):
    enriched_template_mock.return_value = ResourceTemplate(id="123",
                                                           name="template1",
                                                           description="description",
                                                           version="0.1.0",
                                                           resourceType=ResourceType.Workspace,
                                                           current=True,
                                                           required=[],
                                                           properties={},
                                                           customActions=[]).dict()

    template = await resource_repo.validate_input_against_template("template1", workspace_input, ResourceType.Workspace, [])

    assert template.version == "0.1.0"


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
async def test_validate_input_against_template_raises_value_error_if_template_does_not_exist(enriched_template_mock, resource_repo, workspace_input):
    enriched_template_mock.side_effect = EntityDoesNotExist

    with pytest.raises(ValueError):
        await resource_repo.validate_input_against_template("template_name", workspace_input, ResourceType.Workspace, [])


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
async def test_validate_input_against_template_raises_value_error_if_the_user_resource_template_does_not_exist_for_the_given_workspace_service(enriched_template_mock, resource_repo, workspace_input):
    enriched_template_mock.side_effect = EntityDoesNotExist

    with pytest.raises(ValueError):
        await resource_repo.validate_input_against_template("template_name", workspace_input, ResourceType.UserResource, [], "parent_template_name")


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
async def test_validate_input_against_template_raises_value_error_if_payload_is_invalid(enriched_template_mock, resource_repo, workspace_input):
    template_dict = ResourceTemplate(
        id="123",
        name="template1",
        description="description",
        version="0.1.0",
        resourceType=ResourceType.Workspace,
        current=True,
        required=["display_name"],
        properties={},
        customActions=[]).dict()

    # the enrich template method does this
    template_dict.pop("allOf")

    enriched_template_mock.return_value = template_dict

    # missing display name
    workspace_input = WorkspaceInCreate(templateName="template1")

    with pytest.raises(ValidationError):
        await resource_repo.validate_input_against_template("template1", workspace_input, ResourceType.Workspace, [])


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
async def test_validate_input_against_template_raises_if_user_does_not_have_required_role(enriched_template_mock, resource_repo, workspace_input):
    enriched_template_mock.return_value = ResourceTemplate(id="123",
                                                           name="template1",
                                                           description="description",
                                                           version="0.1.0",
                                                           resourceType=ResourceType.Workspace,
                                                           current=True,
                                                           required=[],
                                                           authorizedRoles=["missing_role"],
                                                           properties={},
                                                           customActions=[]).dict()

    with pytest.raises(UserNotAuthorizedToUseTemplate):
        _ = await resource_repo.validate_input_against_template("template1", workspace_input, ResourceType.Workspace, ["test_role", "another_role"])


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
@patch("db.repositories.resources.ResourceRepository._validate_resource_parameters", return_value=None)
async def test_validate_input_against_template_valid_if_user_has_only_one_role(_, enriched_template_mock, resource_repo, workspace_input):
    enriched_template_mock.return_value = ResourceTemplate(id="123",
                                                           name="template1",
                                                           description="description",
                                                           version="0.1.0",
                                                           resourceType=ResourceType.Workspace,
                                                           current=True,
                                                           required=[],
                                                           authorizedRoles=["test_role", "missing_role"],
                                                           properties={},
                                                           customActions=[]).dict()

    template = await resource_repo.validate_input_against_template("template1", workspace_input, ResourceType.Workspace, ["test_role", "another_role"])

    # does not throw
    assert template.version == "0.1.0"


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
@patch("db.repositories.resources.ResourceRepository._validate_resource_parameters", return_value=None)
async def test_validate_input_against_template_valid_if_required_roles_set_is_empty(_, enriched_template_mock, resource_repo, workspace_input):
    enriched_template_mock.return_value = ResourceTemplate(id="123",
                                                           name="template1",
                                                           description="description",
                                                           version="0.1.0",
                                                           resourceType=ResourceType.Workspace,
                                                           current=True,
                                                           required=[],
                                                           properties={},
                                                           customActions=[]).dict()

    template = await resource_repo.validate_input_against_template("template1", workspace_input, ResourceType.Workspace, ["test_user_role"])

    # does not throw
    assert template.version == "0.1.0"


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
async def test_validate_input_against_nested_template_missing_nested_prop(enriched_template_mock, resource_repo):
    enriched_template_mock.return_value = sample_nested_template()
    # missing port
    nested_input = WorkspaceInCreate(templateName="template1")
    nested_input.properties['rules'] = [
        {
            'protocol': {
                'method': 'post'
            }
        }
    ]

    with pytest.raises(ValidationError):
        await resource_repo.validate_input_against_template("template1", nested_input, ResourceType.Workspace)


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
async def test_validate_input_against_nested_template_valid(enriched_template_mock, resource_repo):
    enriched_template_mock.return_value = sample_nested_template()

    # has required props, nested
    nested_input = WorkspaceInCreate(templateName="template1")
    nested_input.properties['rules'] = [
        {
            'protocol': {
                'method': 'post',
                'port': '1234'
            }
        }
    ]

    resp_template = await resource_repo.validate_input_against_template("template1", nested_input, ResourceType.Workspace)
    assert resp_template is not None


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceTemplateRepository.get_current_template")
async def test_get_enriched_template_returns_the_enriched_template(get_current_mock, resource_repo):
    workspace_template = ResourceTemplate(id="abc", name="template1", description="", version="", resourceType=ResourceType.Workspace, current=True, required=[], properties={}, customActions=[])
    get_current_mock.return_value = workspace_template

    template = await resource_repo._get_enriched_template("template1", ResourceType.Workspace)

    get_current_mock.assert_called_once_with('template1', ResourceType.Workspace, '')
    assert "display_name" in template["properties"]


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceTemplateRepository.get_current_template")
async def test_get_enriched_template_returns_the_enriched_template_for_user_resources(get_current_mock, resource_repo):
    user_resource_template = UserResourceTemplate(id="abc", name="template1", description="", version="", resourceType=ResourceType.Workspace, current=True, required=[], properties={}, customActions=[], parentWorkspaceService="parent-template1")
    get_current_mock.return_value = user_resource_template

    template = await resource_repo._get_enriched_template("template1", ResourceType.UserResource, "parent-template1")

    get_current_mock.assert_called_once_with('template1', ResourceType.UserResource, 'parent-template1')
    assert "display_name" in template["properties"]


@pytest.mark.asyncio
async def test_get_resource_dict_by_id_raises_entity_does_not_exist_if_no_resources_come_back(resource_repo):
    item_id = "123"
    resource_repo.read_item_by_id = AsyncMock(side_effect=CosmosResourceNotFoundError)

    with pytest.raises(EntityDoesNotExist):
        await resource_repo.get_resource_dict_by_id(item_id)


@pytest.mark.asyncio
@patch("db.repositories.resources_history.ResourceHistoryRepository.save_item", return_value=AsyncMock())
@patch('db.repositories.resources.ResourceRepository.validate_patch')
@patch('db.repositories.resources.ResourceRepository.get_timestamp', return_value=FAKE_UPDATE_TIMESTAMP)
async def test_patch_resource_preserves_property_history(_, __, ___, resource_repo, resource_history_repo):
    """
    Tests that properties are copied into a history array and only certain values in the root are updated
    """

    resource_repo.update_item_with_etag = AsyncMock(return_value=None)
    resource_patch = ResourcePatch(isEnabled=True, properties={'display_name': 'updated name'})

    etag = "some-etag-value"
    user = create_test_user()

    resource = sample_resource()
    expected_resource = sample_resource()
    expected_resource.properties['display_name'] = 'updated name'
    expected_resource.resourceVersion = 1
    expected_resource.user = user
    expected_resource.updatedWhen = FAKE_UPDATE_TIMESTAMP

    await resource_repo.patch_resource(resource, resource_patch, None, etag, None, resource_history_repo, user, strings.RESOURCE_ACTION_UPDATE)
    resource_repo.update_item_with_etag.assert_called_once_with(expected_resource, etag)

    # now patch again
    new_resource = copy.deepcopy(expected_resource)  # new_resource is after the first patch
    new_patch = ResourcePatch(isEnabled=False, properties={'display_name': 'updated name 2'})
    expected_resource.resourceVersion = 2
    expected_resource.properties['display_name'] = "updated name 2"
    expected_resource.isEnabled = False
    expected_resource.user = user

    await resource_repo.patch_resource(new_resource, new_patch, None, etag, None, resource_history_repo, user, strings.RESOURCE_ACTION_UPDATE)
    resource_repo.update_item_with_etag.assert_called_with(expected_resource, etag)


@patch('db.repositories.resources.ResourceTemplateRepository.enrich_template')
def test_validate_patch_with_good_fields_passes(template_repo, resource_repo):
    """
    Make sure that patch is NOT valid when non-updateable fields are included
    """

    template_repo.enrich_template = MagicMock(return_value=sample_resource_template())
    template = sample_resource_template()

    # check it's valid when updating a single updateable prop
    patch = ResourcePatch(isEnabled=True, properties={'vm_size': 'large'})
    resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)


@patch('db.repositories.resources.ResourceTemplateRepository.enrich_template')
def test_validate_patch_with_bad_fields_fails(template_repo, resource_repo):
    """
    Make sure that patch is NOT valid when non-updateable fields are included
    """

    template_repo.enrich_template = MagicMock(return_value=sample_resource_template())
    template = sample_resource_template()

    # check it's invalid when sending an unexpected field
    patch = ResourcePatch(isEnabled=True, properties={'vm_size': 'large', 'unexpected_field': 'surprise!'})
    with pytest.raises(ValidationError):
        resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_INSTALL)

    # check it's invalid when sending a bad value
    patch = ResourcePatch(isEnabled=True, properties={'vm_size': 'huge'})
    with pytest.raises(ValidationError):
        resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_INSTALL)

    # check it's invalid when trying to update a non-updateable field
    patch = ResourcePatch(isEnabled=True, properties={'vm_size': 'large', 'os_image': 'linux'})
    with pytest.raises(ValidationError):
        resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_INSTALL)
