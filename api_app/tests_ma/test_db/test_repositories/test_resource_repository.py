import copy
from unittest.mock import AsyncMock
import uuid
import pytest
import pytest_asyncio
from mock import patch, MagicMock
from pydantic import parse_obj_as

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
from models.domain.user_resource import UserResource
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
                                        'Windows 11',
                                        'Windows Server 2025'
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


def sample_resource_template_with_new_property(version: str = "0.2.0") -> dict:
    """
    Returns a template similar to sample_resource_template but with an additional
    'new_property' that is not updateable. Useful for testing template upgrades.
    """
    return ResourceTemplate(
        id="123",
        name="tre-user-resource",
        description="description",
        version=version,
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
                    'Windows 11',
                    'Windows Server 2025'
                ],
                'updateable': False
            },
            'vm_size': {
                'type': 'string',
                'title': 'VM Size',
                'description': 'Select Windows image to use for VM',
                'enum': [
                    'small',
                    'large'
                ],
                'updateable': True
            },
            'new_property': {
                'type': 'string',
                'title': 'New non-updateable property',
                'enum': [
                    'value1',
                    'value2'
                ],
                'updateable': False
            }
        },
        actions=[]
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


@pytest.mark.asyncio
async def test_validate_patch_with_good_fields_passes(resource_repo):
    """
    Make sure that patch is valid when updateable fields are included
    """
    template_repo = MagicMock()
    template_repo.enrich_template = MagicMock(return_value=sample_resource_template())
    template = sample_resource_template()

    # check it's valid when updating a single updateable prop
    patch = ResourcePatch(isEnabled=True, properties={'vm_size': 'large'})
    await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)


@pytest.mark.asyncio
async def test_validate_patch_with_bad_fields_fails(resource_repo):
    """
    Make sure that patch is NOT valid when non-updateable fields are included
    """
    template_repo = MagicMock()
    template_repo.enrich_template = MagicMock(return_value=sample_resource_template())
    template = sample_resource_template()

    # check it's invalid when sending an unexpected field
    patch = ResourcePatch(isEnabled=True, properties={'vm_size': 'large', 'unexpected_field': 'surprise!'})
    with pytest.raises(ValidationError, match="Property 'unexpected_field' is unexpected."):
        await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)

    # check it's invalid when sending a bad value (new install)
    patch = ResourcePatch(isEnabled=True, properties={'vm_size': 'huge'})
    with pytest.raises(ValidationError):
        await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_INSTALL)

    # check it's invalid when sending a bad value (update)
    patch = ResourcePatch(isEnabled=True, properties={'vm_size': 'huge'})
    with pytest.raises(ValidationError):
        await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)

    # check it's invalid when trying to update a non-updateable field
    patch = ResourcePatch(isEnabled=True, properties={'vm_size': 'large', 'os_image': 'Windows 11'})
    with pytest.raises(ValidationError, match="Property 'os_image' is not updateable."):
        await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)


@pytest.mark.asyncio
async def test_validate_patch_allows_new_non_updateable_property_during_upgrade(resource_repo):
    """
    Test that during a template upgrade, new properties (not in old version) can be specified
    even if they are marked as updateable: false in the new template version
    """
    # Old template has os_image and vm_size
    old_template = sample_resource_template()
    old_template['version'] = '0.1.0'

    # New template adds a new property 'new_property' that is not updateable
    new_template = sample_resource_template_with_new_property(version='0.2.0')

    # Mock the template repository
    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(return_value=parse_obj_as(ResourceTemplate, new_template))
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    # Patch includes the new property during upgrade - this should be ALLOWED
    patch = ResourcePatch(templateVersion='0.2.0', properties={'new_property': 'value1'})
    current_properties = {'title': 'Test Title', 'os_image': 'Windows 11', 'vm_size': 'small'}

    # This should NOT raise a ValidationError
    await resource_repo.validate_patch(
        patch,
        template_repo,
        parse_obj_as(ResourceTemplate, old_template),
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties
    )


@pytest.mark.asyncio
async def test_validate_patch_rejects_existing_non_updateable_property_during_upgrade(resource_repo):
    """
    Test that during a template upgrade, existing non-updateable properties still cannot be modified
    """
    # Old template has os_image (non-updateable) and vm_size (updateable)
    old_template = sample_resource_template()

    # New template is the same but version 0.2.0
    new_template = copy.deepcopy(old_template)

    # Mock the template repository
    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(return_value=parse_obj_as(ResourceTemplate, new_template))
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    # Try to update existing non-updateable property during upgrade - this should FAIL
    patch = ResourcePatch(templateVersion='0.2.0', properties={'os_image': 'Windows Server 2025'})

    with pytest.raises(ValidationError):
        await resource_repo.validate_patch(patch, template_repo, parse_obj_as(ResourceTemplate, old_template), strings.RESOURCE_ACTION_UPDATE)


@pytest.mark.asyncio
async def test_validate_patch_allows_unchanged_null_property_during_upgrade(resource_repo):
    """
    Test that during a template upgrade, non-updateable properties with existing None/null value sent unchanged pass validation.
    """
    old_template = sample_resource_template()
    new_template = copy.deepcopy(old_template)
    new_template['version'] = '0.2.0'

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(return_value=parse_obj_as(ResourceTemplate, new_template))
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    current_properties = {
        'os_image': None,
        'vm_size': 'small'
    }

    patch = ResourcePatch(templateVersion='0.2.0', properties={'os_image': None})

    resource_repo._validate_resource_parameters = MagicMock()

    await resource_repo.validate_patch(
        patch,
        template_repo,
        parse_obj_as(ResourceTemplate, old_template),
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties
    )


@pytest.mark.asyncio
async def test_validate_patch_evaluates_allof_condition_against_current_properties(resource_repo):
    """
    Test that during upgrade, allOf conditional branches depending on existing properties evaluate against merged state.
    """
    old_template = sample_resource_template()
    old_template['properties']['auth_type'] = {
        'type': 'string',
        'updateable': False
    }

    new_template = copy.deepcopy(old_template)
    new_template['version'] = '0.2.0'
    new_template['properties']['oauth_client_id'] = {'type': 'string'}
    new_template['allOf'] = [
        {
            'if': {
                'properties': {'auth_type': {'const': 'OAuth'}}
            },
            'then': {
                'properties': {'oauth_client_id': {'type': 'string'}}
            }
        }
    ]
    new_template['unevaluatedProperties'] = False

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(return_value=parse_obj_as(ResourceTemplate, new_template))
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    current_properties = {
        'auth_type': 'OAuth',
        'title': 'Test Title',
        'os_image': 'Windows 11',
        'vm_size': 'small'
    }

    patch = ResourcePatch(templateVersion='0.2.0', properties={'oauth_client_id': 'client_123'})

    await resource_repo.validate_patch(
        patch,
        template_repo,
        parse_obj_as(ResourceTemplate, old_template),
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties
    )


@pytest.mark.asyncio
async def test_validate_patch_rejects_system_properties_modification_during_upgrade(resource_repo):
    """
    Test that during a template upgrade, system properties (e.g. tre_id) are not treated as new properties and cannot be modified.
    """
    old_template_dict = sample_resource_template()
    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict['version'] = '0.2.0'

    old_template = parse_obj_as(ResourceTemplate, old_template_dict)
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(return_value=new_template)
    template_repo.enrich_template = MagicMock(side_effect=lambda t, is_update=False: {
        **t.dict(),
        'system_properties': {'tre_id': {'type': 'string'}}
    })

    current_properties = {
        'tre_id': 'old_tre_id',
        'title': 'Test Title',
        'os_image': 'Windows 11',
        'vm_size': 'small'
    }

    patch = ResourcePatch(templateVersion='0.2.0', properties={'tre_id': 'new_tre_id'})

    with pytest.raises(ValidationError):
        await resource_repo.validate_patch(
            patch,
            template_repo,
            old_template,
            strings.RESOURCE_ACTION_UPDATE,
            current_properties=current_properties
        )


@pytest.mark.asyncio
async def test_validate_patch_allows_enum_property_update_during_upgrade_when_existing_value_is_invalid(resource_repo):
    """
    Test that during a template upgrade, updating a non-updateable enum property is allowed when the resource's current value is no longer in the target template's enum list.
    """
    old_template = sample_resource_template()

    new_template = copy.deepcopy(old_template)
    new_template['version'] = '0.2.0'
    new_template['properties']['os_image']['enum'] = ['Windows 11 Enterprise', 'Windows Server 2025']

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(return_value=parse_obj_as(ResourceTemplate, new_template))
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    current_properties = {
        'title': 'Test Title',
        'os_image': 'Windows 11',
        'vm_size': 'small'
    }

    patch = ResourcePatch(templateVersion='0.2.0', properties={'os_image': 'Windows 11 Enterprise'})

    await resource_repo.validate_patch(
        patch,
        template_repo,
        parse_obj_as(ResourceTemplate, old_template),
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties
    )


@pytest.mark.asyncio
async def test_validate_patch_allows_retained_system_properties_with_unevaluated_properties_false(resource_repo):
    """
    Test that during upgrade, retained system properties in current_properties pass validation when unevaluatedProperties is False.
    """
    old_template_dict = sample_resource_template()
    old_template_dict['unevaluatedProperties'] = False

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict['version'] = '0.2.0'
    new_template_dict['unevaluatedProperties'] = False

    old_template = parse_obj_as(ResourceTemplate, old_template_dict)
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(return_value=new_template)
    template_repo.enrich_template = MagicMock(side_effect=lambda t, is_update=False: {
        **t.dict(exclude_none=True),
        'unevaluatedProperties': False,
        'system_properties': {'tre_id': {'type': 'string'}}
    })

    current_properties = {
        'tre_id': 'tre-1234',
        'title': 'Test Title',
        'os_image': 'Windows 11',
        'vm_size': 'small'
    }

    patch = ResourcePatch(templateVersion='0.2.0', properties={'vm_size': 'large'})

    await resource_repo.validate_patch(
        patch,
        template_repo,
        old_template,
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties
    )


@pytest.mark.asyncio
async def test_validate_patch_rejects_empty_object_for_non_updateable_property(resource_repo):
    """
    Test that sending an empty dict for a non-updateable object property is validated and rejected.
    """
    template_dict = sample_resource_template()
    template_dict['properties']['parent_object'] = {
        'type': 'object',
        'updateable': False,
        'properties': {
            'child_prop': {'type': 'string'}
        }
    }
    template = parse_obj_as(ResourceTemplate, template_dict)

    template_repo = MagicMock()
    template_repo.enrich_template = MagicMock(return_value=template_dict)

    patch = ResourcePatch(isEnabled=True, properties={'parent_object': {}})

    with pytest.raises(ValidationError, match="Property 'parent_object' is not updateable."):
        await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)


@pytest.mark.asyncio
async def test_validate_patch_allows_updateable_property_during_upgrade(resource_repo):
    """
    Test that during a template upgrade, updateable properties can still be modified
    """
    # Old template 0.1.0
    old_template = sample_resource_template()

    # New template 0.2.0
    new_template = copy.deepcopy(old_template)

    # Mock the template repository
    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(return_value=parse_obj_as(ResourceTemplate, new_template))
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    # Update existing updateable property during upgrade - this should work
    patch = ResourcePatch(templateVersion='0.2.0', properties={'vm_size': 'large'})
    current_properties = {'title': 'Test Title', 'os_image': 'Windows 11', 'vm_size': 'small'}

    # This should NOT raise a ValidationError
    await resource_repo.validate_patch(
        patch,
        template_repo,
        parse_obj_as(ResourceTemplate, old_template),
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties
    )


@pytest.mark.asyncio
async def test_validate_patch_allows_mix_of_new_and_updateable_properties_during_upgrade(resource_repo):
    """
    Test that during upgrade, you can specify both new non-updateable properties and existing updateable properties
    """
    # Old template
    old_template = sample_resource_template()

    # New template adds new_property
    new_template = sample_resource_template_with_new_property(version='0.2.0')

    # Mock the template repository
    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(return_value=parse_obj_as(ResourceTemplate, new_template))
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    # Patch with both new non-updateable property and existing updateable property
    patch = ResourcePatch(templateVersion='0.2.0', properties={'new_property': 'value1', 'vm_size': 'large'})
    current_properties = {'title': 'Test Title', 'os_image': 'Windows 11', 'vm_size': 'small'}

    # This should NOT raise a ValidationError
    await resource_repo.validate_patch(
        patch,
        template_repo,
        parse_obj_as(ResourceTemplate, old_template),
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties
    )


@pytest.mark.asyncio
async def test_validate_patch_rejects_user_patch_for_non_updateable_install_pipeline_property(resource_repo):
    """
    Make sure that external user PATCH cannot modify a non-updateable property even if it is in an install pipeline.
    """

    template_dict = sample_resource_template()
    template_dict['properties']['my_inherited_property'] = {
        'type': 'string',
        'updateable': False
    }
    template_dict['pipeline'] = {
        'install': [
            {
                'stepId': 'main',
                'properties': [
                    {'name': 'my_inherited_property', 'value': '{{ resource.parent.properties.my_inherited_property }}', 'type': 'string'}
                ]
            }
        ]
    }

    template_repo = MagicMock()
    template_repo.enrich_template = MagicMock(return_value=template_dict)
    template = parse_obj_as(ResourceTemplate, template_dict)

    patch = ResourcePatch(isEnabled=True, properties={'my_inherited_property': 'new_val'})

    with pytest.raises(ValidationError, match="Property 'my_inherited_property' is not updateable."):
        await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)


@pytest.mark.asyncio
async def test_validate_patch_rejects_user_patch_for_non_updateable_upgrade_pipeline_property(resource_repo):
    """
    Make sure that external user PATCH cannot modify a non-updateable property even if it is in an upgrade pipeline.
    """

    template_dict = sample_resource_template()
    template_dict['properties']['my_inherited_property'] = {
        'type': 'string',
        'updateable': False
    }
    template_dict['pipeline'] = {
        'upgrade': [
            {
                'stepId': 'main',
                'properties': [
                    {'name': 'my_inherited_property', 'value': '{{ resource.parent.properties.my_inherited_property }}', 'type': 'string'}
                ]
            }
        ]
    }

    template_repo = MagicMock()
    template_repo.enrich_template = MagicMock(return_value=template_dict)
    template = parse_obj_as(ResourceTemplate, template_dict)

    patch = ResourcePatch(isEnabled=True, properties={'my_inherited_property': 'new_val'})

    with pytest.raises(ValidationError, match="Property 'my_inherited_property' is not updateable."):
        await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)


@pytest.mark.asyncio
async def test_validate_patch_enforces_newly_required_properties_during_upgrade(resource_repo):
    """
    Test that during an upgrade, newly required properties defined in the target template are enforced.
    """
    old_template_dict = sample_resource_template()
    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict['version'] = '0.2.0'
    new_template_dict['properties']['new_req_prop'] = {'type': 'string'}
    new_template_dict['required'].append('new_req_prop')

    old_template = parse_obj_as(ResourceTemplate, old_template_dict)
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(return_value=new_template)
    template_repo.enrich_template = MagicMock(side_effect=[old_template_dict, new_template_dict])

    current_properties = {
        'display_name': 'Test Resource',
        'vm_size': 'small'
    }

    # Omit new_req_prop from patch -> should raise ValidationError
    patch = ResourcePatch(templateVersion='0.2.0', properties={'vm_size': 'large'})

    with pytest.raises(ValidationError):
        await resource_repo.validate_patch(
            patch,
            template_repo,
            old_template,
            strings.RESOURCE_ACTION_UPDATE,
            current_properties=current_properties
        )


@pytest.mark.asyncio
async def test_get_all_property_keys_from_template_includes_allOf_conditional_properties(resource_repo):
    """
    Test that _get_all_property_keys_from_template correctly collects properties defined
    in conditional allOf blocks (both then and else clauses).
    """
    template_dict = sample_resource_template()
    template_dict['allOf'] = [
        {
            "if": {
                "properties": {
                    "vm_size": {"const": "small"}
                }
            },
            "then": {
                "properties": {
                    "conditional_then_property": {"type": "string"}
                }
            },
            "else": {
                "properties": {
                    "conditional_else_property": {"type": "string"}
                }
            }
        }
    ]
    template = parse_obj_as(ResourceTemplate, template_dict)

    properties = resource_repo._get_all_property_keys_from_template(template)

    assert "conditional_then_property" in properties
    assert "conditional_else_property" in properties
    assert "vm_size" in properties


@pytest.mark.asyncio
async def test_validate_patch_allows_partial_update_on_nested_object_with_required_fields(resource_repo):
    """
    Test that validate_patch allows partial update of nested object properties even if the schema
    defines nested required fields.
    """
    template_repo = MagicMock()
    template_dict = sample_resource_template()
    template_dict["properties"]["parent_obj"] = {
        "type": "object",
        "updateable": True,
        "required": ["child_a", "child_b"],
        "properties": {
            "child_a": {"type": "string"},
            "child_b": {"type": "string"}
        }
    }
    template_repo.enrich_template = MagicMock(return_value=template_dict)
    template = parse_obj_as(ResourceTemplate, template_dict)

    patch = ResourcePatch(properties={"parent_obj": {"child_b": "new_value"}})

    # Should pass without raising ValidationError for missing sibling field child_a
    await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)


@pytest.mark.asyncio
@patch('db.repositories.resources.ResourceTemplateRepository.enrich_template')
async def test_validate_patch_rejects_non_updateable_allOf_property(enrich_template_mock, resource_repo):
    """
    Test that validate_patch rejects attempts to patch non-updateable conditional properties inside allOf
    """
    template_dict = sample_resource_template()
    template_dict['allOf'] = [
        {
            "if": {"properties": {"vm_size": {"const": "small"}}},
            "then": {"properties": {"secret_conditional_field": {"type": "string", "updateable": False}}}
        }
    ]
    template = parse_obj_as(ResourceTemplate, template_dict)
    enrich_template_mock.return_value = template_dict

    template_repo = MagicMock()
    template_repo.enrich_template = enrich_template_mock

    # Resource has vm_size small, patching secret_conditional_field should be denied since updateable: False
    patch = ResourcePatch(properties={"secret_conditional_field": "new_secret"})

    with pytest.raises(ValidationError):
        await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)


@pytest.mark.asyncio
@patch('db.repositories.resources.ResourceTemplateRepository.get_template_by_name_and_version')
@patch('db.repositories.resources.ResourceTemplateRepository.enrich_template')
async def test_validate_patch_allows_new_nested_property_under_existing_object_during_upgrade(enrich_template_mock, get_template_mock, resource_repo):
    """
    Test that during an upgrade, adding a newly-introduced nested property inside an existing object
    passes validation even if the parent object is not marked updateable.
    """
    old_template_dict = sample_resource_template()
    old_template_dict['properties']['parent_object'] = {
        'type': 'object',
        'updateable': False,
        'properties': {
            'existing_child': {'type': 'string', 'updateable': False}
        }
    }
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict['version'] = '0.2.0'
    new_template_dict['properties']['parent_object']['properties']['new_child'] = {
        'type': 'string',
        'updateable': False
    }
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    get_template_mock.return_value = new_template
    enrich_template_mock.side_effect = [old_template_dict, new_template_dict]

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = get_template_mock
    template_repo.enrich_template = enrich_template_mock

    current_properties = {
        'title': 'Test Title',
        'os_image': 'Windows 11',
        'vm_size': 'small',
        'parent_object': {'existing_child': 'old_val'}
    }

    # Patching new_child during upgrade should be allowed
    patch = ResourcePatch(templateVersion='0.2.0', properties={'parent_object': {'new_child': 'new_val'}})
    await resource_repo.validate_patch(patch, template_repo, old_template, strings.RESOURCE_ACTION_UPDATE, current_properties=current_properties)


@pytest.mark.asyncio
@patch('db.repositories.resources.ResourceTemplateRepository.get_template_by_name_and_version')
async def test_validate_patch_rejects_modifying_existing_nested_non_updateable_property_during_upgrade(get_template_mock, resource_repo):
    """
    Test that during an upgrade, attempting to modify an existing non-updateable nested property
    fails validation.
    """
    old_template_dict = sample_resource_template()
    old_template_dict['properties']['parent_object'] = {
        'type': 'object',
        'updateable': False,
        'properties': {
            'existing_child': {'type': 'string', 'updateable': False}
        }
    }
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict['version'] = '0.2.0'
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    get_template_mock.return_value = new_template
    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = get_template_mock
    template_repo.enrich_template = MagicMock(return_value=new_template_dict)

    current_properties = {
        'title': 'Test Title',
        'os_image': 'Windows 11',
        'vm_size': 'small',
        'parent_object': {'existing_child': 'old_val'}
    }

    # Attempting to change existing_child during upgrade should raise ValidationError
    patch = ResourcePatch(templateVersion='0.2.0', properties={'parent_object': {'existing_child': 'modified_val'}})
    with pytest.raises(ValidationError):
        await resource_repo.validate_patch(patch, template_repo, old_template, strings.RESOURCE_ACTION_UPDATE, current_properties=current_properties)


@pytest.mark.asyncio
@patch('db.repositories.resources.ResourceTemplateRepository.get_template_by_name_and_version')
async def test_patch_resource_removes_nested_properties_on_upgrade(get_template_mock, resource_repo, resource_history_repo):
    """
    Test that patch_resource removes nested properties that were deleted in the new template version.
    """
    resource_repo.update_item_with_etag = AsyncMock(return_value=None)
    resource_history_repo.create_resource_history_item = AsyncMock()

    old_template_dict = sample_resource_template()
    old_template_dict['properties']['parent_object'] = {
        'type': 'object',
        'properties': {
            'kept_child': {'type': 'string'},
            'removed_child': {'type': 'string'}
        }
    }
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict['version'] = '0.2.0'
    del new_template_dict['properties']['parent_object']['properties']['removed_child']
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    resource_repo.validate_template_version_patch = AsyncMock(return_value=new_template)

    get_template_mock.return_value = new_template
    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = get_template_mock
    template_repo.enrich_template = MagicMock(return_value=new_template_dict)

    user = create_test_user()
    resource = sample_resource()
    resource.properties = {
        'title': 'Test Title',
        'os_image': 'Windows 11',
        'vm_size': 'small',
        'parent_object': {
            'kept_child': 'val1',
            'removed_child': 'val2'
        }
    }

    patch = ResourcePatch(templateVersion='0.2.0', properties={})

    _, returned_template = await resource_repo.patch_resource(
        resource,
        patch,
        old_template,
        "some-etag",
        template_repo,
        resource_history_repo,
        user,
        strings.RESOURCE_ACTION_UPDATE
    )

    assert 'removed_child' not in resource.properties['parent_object']
    assert resource.properties['parent_object']['kept_child'] == 'val1'
    assert returned_template == new_template


@pytest.mark.asyncio
async def test_patch_resource_allows_full_array_items_when_adding_property(resource_repo, resource_history_repo):
    """Full array items sent by an upgrade remain valid when only one item property is new."""
    resource_repo.update_item_with_etag = AsyncMock(return_value=None)
    resource_history_repo.create_resource_history_item = AsyncMock()

    old_template_dict = sample_resource_template()
    old_template_dict['properties']['redirect_uris'] = {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'}
            }
        }
    }
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict['version'] = '0.2.0'
    new_template_dict['properties']['redirect_uris']['items']['properties']['value'] = {
        'type': 'string',
        'default': 'https://example.test'
    }
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    resource_repo.validate_template_version_patch = AsyncMock(return_value=new_template)
    template_repo = MagicMock()

    def enrich_template(template, is_update=False):
        enriched = copy.deepcopy(new_template_dict if template.version == '0.2.0' else old_template_dict)
        if not enriched.get('allOf'):
            enriched.pop('allOf', None)
        return enriched

    template_repo.enrich_template.side_effect = enrich_template

    user = create_test_user()
    resource = sample_resource()
    resource.properties = {
        'title': 'Test Title',
        'os_image': 'Windows 11',
        'vm_size': 'small',
        'redirect_uris': [{'name': 'primary'}]
    }
    patch = ResourcePatch(
        templateVersion='0.2.0',
        properties={'redirect_uris': [{'name': 'primary', 'value': 'https://example.test'}]}
    )

    updated_resource, returned_template = await resource_repo.patch_resource(
        resource,
        patch,
        old_template,
        'some-etag',
        template_repo,
        resource_history_repo,
        user,
        strings.RESOURCE_ACTION_UPDATE
    )

    assert updated_resource.properties['redirect_uris'] == [{'name': 'primary', 'value': 'https://example.test'}]
    assert returned_template == new_template


@pytest.mark.asyncio
@patch('db.repositories.resources.ResourceTemplateRepository.get_template_by_name_and_version')
@patch('db.repositories.resources.ResourceTemplateRepository.enrich_template')
async def test_validate_patch_passes_parent_service_name_for_user_resources(enrich_template_mock, get_template_mock, resource_repo):
    """
    Test that during a template upgrade for a UserResource, parent_service_name is passed
    to get_template_by_name_and_version.
    """
    old_template_dict = sample_resource_template()
    old_template_dict['resourceType'] = ResourceType.UserResource
    old_template_dict['parentWorkspaceService'] = 'parent-service-name'
    old_template = parse_obj_as(UserResourceTemplate, old_template_dict)

    new_template = copy.deepcopy(old_template)
    new_template.version = '0.2.0'
    get_template_mock.return_value = new_template
    enrich_template_mock.return_value = old_template_dict

    # Mock template repository
    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = get_template_mock
    template_repo.enrich_template = enrich_template_mock

    patch = ResourcePatch(templateVersion='0.2.0', properties={})
    current_properties = {'title': 'Test Title', 'os_image': 'Windows 11', 'vm_size': 'small'}
    await resource_repo.validate_patch(patch, template_repo, old_template, strings.RESOURCE_ACTION_UPDATE, current_properties=current_properties)

    get_template_mock.assert_called_once_with(
        old_template.name,
        '0.2.0',
        ResourceType.UserResource,
        parent_service_name='parent-service-name'
    )


@pytest.mark.asyncio
@patch('db.repositories.resources.ResourceRepository.create')
@patch('db.repositories.resources.ResourceTemplateRepository.get_template_by_name_and_version')
@patch('db.repositories.resources.ResourceTemplateRepository.enrich_template')
async def test_patch_resource_passes_parent_service_name_for_user_resources(enrich_template_mock, get_template_mock, create_repo_mock, resource_repo, resource_history_repo):
    """
    Test that patch_resource passes parent_service_name to get_template_by_name_and_version
    when upgrading a UserResource.
    """
    resource_repo.update_item_with_etag = AsyncMock(return_value=None)
    resource_history_repo.create_resource_history_item = AsyncMock()

    mock_parent_repo = AsyncMock()
    mock_parent_repo.get_resource_by_id.return_value = MagicMock(templateName='parent-service-name')
    create_repo_mock.return_value = mock_parent_repo

    old_template_dict = sample_resource_template()
    old_template_dict['resourceType'] = ResourceType.UserResource
    old_template_dict['parentWorkspaceService'] = 'parent-service-name'
    old_template = parse_obj_as(UserResourceTemplate, old_template_dict)

    new_template = copy.deepcopy(old_template)
    new_template.version = '0.2.0'
    get_template_mock.return_value = new_template
    enrich_template_mock.return_value = old_template_dict

    # Mock template repository
    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = get_template_mock
    template_repo.enrich_template = enrich_template_mock

    user = create_test_user()
    resource_dict = sample_resource().dict()
    resource_dict['resourceType'] = ResourceType.UserResource
    resource_dict['parentWorkspaceServiceId'] = 'parent-service-id'
    resource_dict['templateVersion'] = '0.1.0'
    resource_dict['properties'] = {'title': 'Test Title', 'os_image': 'Windows 11', 'vm_size': 'small'}
    resource = parse_obj_as(UserResource, resource_dict)

    resource_patch = ResourcePatch(templateVersion='0.2.0', properties={})

    await resource_repo.patch_resource(
        resource,
        resource_patch,
        old_template,
        "some-etag",
        template_repo,
        resource_history_repo,
        user,
        strings.RESOURCE_ACTION_UPDATE
    )

    get_template_mock.assert_called_once_with(
        resource.templateName,
        '0.2.0',
        ResourceType.UserResource,
        'parent-service-name'
    )


def test_deep_dict_update_preserves_nested_siblings(resource_repo):
    target = {
        "display_name": "My Resource",
        "parent_object": {
            "sibling_field": "existing_value",
            "target_field": "old_value"
        }
    }
    patch = {
        "parent_object": {
            "target_field": "new_value",
            "added_field": "added_value"
        }
    }
    resource_repo._deep_dict_update(target, patch)
    assert target == {
        "display_name": "My Resource",
        "parent_object": {
            "sibling_field": "existing_value",
            "target_field": "new_value",
            "added_field": "added_value"
        }
    }


@pytest.mark.asyncio
@patch('db.repositories.resources.ResourceTemplateRepository.get_template_by_name_and_version')
@patch('db.repositories.resources.ResourceTemplateRepository.enrich_template')
async def test_validate_patch_allows_absent_target_required_non_updateable_property_on_upgrade(enrich_template_mock, get_template_mock, resource_repo):
    """
    Test that an optional non-updateable property from the old template that becomes required in
    the target version can be initially populated on upgrade if absent from current properties.
    """
    old_template_dict = sample_resource_template()
    old_template_dict['properties']['newly_required'] = {
        'type': 'string',
        'title': 'Newly Required Non-Updateable',
        'updateable': False
    }
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    target_template_dict = copy.deepcopy(old_template_dict)
    target_template_dict['version'] = '0.2.0'
    target_template_dict['required'].append('newly_required')
    target_template = parse_obj_as(ResourceTemplate, target_template_dict)

    get_template_mock.return_value = target_template
    enrich_template_mock.return_value = target_template_dict

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = get_template_mock
    template_repo.enrich_template = enrich_template_mock

    # Resource current properties omit 'newly_required'
    current_properties = {
        'title': 'Test Title',
        'os_image': 'Windows 11',
        'vm_size': 'small'
    }

    # Patch supplies 'newly_required' during upgrade
    patch = ResourcePatch(templateVersion='0.2.0', properties={'newly_required': 'initial_value'})

    # Validation should succeed without throwing ValidationError
    await resource_repo.validate_patch(
        patch,
        template_repo,
        old_template,
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties,
        target_template=target_template
    )


@pytest.mark.asyncio
@patch('db.repositories.resources.ResourceTemplateRepository.get_template_by_name_and_version')
async def test_patch_resource_preserves_runtime_properties_on_upgrade(get_template_mock, resource_repo, resource_history_repo):
    """
    Test that patch_resource preserves API-injected/runtime properties (e.g. workspace_subscription_id)
    that are absent from both current and target template schemas.
    """
    resource_repo.update_item_with_etag = AsyncMock(return_value=None)
    resource_history_repo.create_resource_history_item = AsyncMock()

    old_template_dict = sample_resource_template()
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict['version'] = '0.2.0'
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    resource_repo.validate_template_version_patch = AsyncMock(return_value=new_template)
    get_template_mock.return_value = new_template

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = get_template_mock
    template_repo.enrich_template = MagicMock(return_value=new_template_dict)

    user = create_test_user()
    resource = sample_resource()
    resource.properties = {
        'title': 'Test Title',
        'os_image': 'Windows 11',
        'vm_size': 'small',
        'workspace_subscription_id': 'sub-123-abc'  # Runtime property not in template schema
    }

    patch = ResourcePatch(templateVersion='0.2.0', properties={})

    updated_resource, _ = await resource_repo.patch_resource(
        resource,
        patch,
        old_template,
        "some-etag",
        template_repo,
        resource_history_repo,
        user,
        strings.RESOURCE_ACTION_UPDATE
    )

    assert updated_resource.properties.get('workspace_subscription_id') == 'sub-123-abc'
