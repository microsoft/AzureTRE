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
from db.repositories.resources import (
    ResourceRepository,
    mask_sensitive_properties,
    masked_property_paths,
    restore_sensitive_values,
    set_masked_values,
)
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
    with patch("api.dependencies.database.Database.get_container_proxy", return_value=None):
        resource_repo = await ResourceRepository().create()
        yield resource_repo


@pytest_asyncio.fixture
async def resource_history_repo():
    with patch("api.dependencies.database.Database.get_container_proxy", return_value=None):
        resource_history_repo = await ResourceHistoryRepository().create()
        yield resource_history_repo


@pytest.fixture
def workspace_input():
    return WorkspaceInCreate(
        templateName="base-tre", properties={"display_name": "test", "description": "test", "client_id": "123"}
    )


def sample_resource() -> Resource:
    return Resource(
        id=RESOURCE_ID,
        isEnabled=True,
        resourcePath="/resource/path",
        templateName="template_name",
        templateVersion="template_version",
        properties={
            "display_name": "initial display name",
            "description": "initial description",
            "computed_prop": "computed_val",
        },
        resourceType=ResourceType.Workspace,
        etag="some-etag-value",
        resourceVersion=0,
        updatedWhen=FAKE_CREATE_TIMESTAMP,
        user=create_test_user(),
    )


def sample_resource_template() -> ResourceTemplate:
    return ResourceTemplate(
        id="123",
        name="tre-user-resource",
        description="description",
        version="0.1.0",
        resourceType=ResourceType.UserResource,
        current=True,
        required=["os_image", "title"],
        properties={
            "title": {"type": "string", "title": "Title of the resource"},
            "os_image": {
                "type": "string",
                "title": "Windows image",
                "description": "Select Windows image to use for VM",
                "enum": ["Windows 11", "Server 2019 Data Science VM", "Server 2022 Data Science VM"],
                "updateable": False,
            },
            "vm_size": {
                "type": "string",
                "title": "Windows image",
                "description": "Select Windows image to use for VM",
                "enum": ["small", "large"],
                "updateable": True,
            },
        },
        actions=[],
    ).model_dump(exclude_none=True)


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
            "rules": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [],
                    "properties": {
                        "protocol": {
                            "type": "object",
                            "required": ["port"],
                            "items": {
                                "type": "object",
                                "properties": {"port": {"type": "string"}, "method": {"type": "string"}},
                            },
                        }
                    },
                },
            }
        },
        customActions=[],
    ).model_dump(exclude_none=True)


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
@patch("db.repositories.resources.ResourceRepository._validate_resource_parameters", return_value=None)
async def test_validate_input_against_template_returns_template_version_if_template_is_valid(
    _, enriched_template_mock, resource_repo, workspace_input
):
    enriched_template_mock.return_value = ResourceTemplate(
        id="123",
        name="template1",
        description="description",
        version="0.1.0",
        resourceType=ResourceType.Workspace,
        current=True,
        required=[],
        properties={},
        customActions=[],
    ).model_dump()

    template = await resource_repo.validate_input_against_template(
        "template1", workspace_input, ResourceType.Workspace, []
    )

    assert template.version == "0.1.0"


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
async def test_validate_input_against_template_raises_value_error_if_template_does_not_exist(
    enriched_template_mock, resource_repo, workspace_input
):
    enriched_template_mock.side_effect = EntityDoesNotExist

    with pytest.raises(ValueError):
        await resource_repo.validate_input_against_template(
            "template_name", workspace_input, ResourceType.Workspace, []
        )


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
async def test_validate_input_against_template_raises_value_error_if_the_user_resource_template_does_not_exist_for_the_given_workspace_service(
    enriched_template_mock, resource_repo, workspace_input
):
    enriched_template_mock.side_effect = EntityDoesNotExist

    with pytest.raises(ValueError):
        await resource_repo.validate_input_against_template(
            "template_name", workspace_input, ResourceType.UserResource, [], "parent_template_name"
        )


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
async def test_validate_input_against_template_raises_value_error_if_payload_is_invalid(
    enriched_template_mock, resource_repo, workspace_input
):
    template_dict = ResourceTemplate(
        id="123",
        name="template1",
        description="description",
        version="0.1.0",
        resourceType=ResourceType.Workspace,
        current=True,
        required=["display_name"],
        properties={},
        customActions=[],
    ).model_dump()

    enriched_template_mock.return_value = template_dict

    # missing display name
    workspace_input = WorkspaceInCreate(templateName="template1")

    with pytest.raises(ValidationError):
        await resource_repo.validate_input_against_template("template1", workspace_input, ResourceType.Workspace, [])


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
async def test_validate_input_against_template_raises_if_user_does_not_have_required_role(
    enriched_template_mock, resource_repo, workspace_input
):
    enriched_template_mock.return_value = ResourceTemplate(
        id="123",
        name="template1",
        description="description",
        version="0.1.0",
        resourceType=ResourceType.Workspace,
        current=True,
        required=[],
        authorizedRoles=["missing_role"],
        properties={},
        customActions=[],
    ).model_dump()

    with pytest.raises(UserNotAuthorizedToUseTemplate):
        _ = await resource_repo.validate_input_against_template(
            "template1", workspace_input, ResourceType.Workspace, ["test_role", "another_role"]
        )


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
@patch("db.repositories.resources.ResourceRepository._validate_resource_parameters", return_value=None)
async def test_validate_input_against_template_valid_if_user_has_only_one_role(
    _, enriched_template_mock, resource_repo, workspace_input
):
    enriched_template_mock.return_value = ResourceTemplate(
        id="123",
        name="template1",
        description="description",
        version="0.1.0",
        resourceType=ResourceType.Workspace,
        current=True,
        required=[],
        authorizedRoles=["test_role", "missing_role"],
        properties={},
        customActions=[],
    ).model_dump()

    template = await resource_repo.validate_input_against_template(
        "template1", workspace_input, ResourceType.Workspace, ["test_role", "another_role"]
    )

    # does not throw
    assert template.version == "0.1.0"


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
@patch("db.repositories.resources.ResourceRepository._validate_resource_parameters", return_value=None)
async def test_validate_input_against_template_valid_if_required_roles_set_is_empty(
    _, enriched_template_mock, resource_repo, workspace_input
):
    enriched_template_mock.return_value = ResourceTemplate(
        id="123",
        name="template1",
        description="description",
        version="0.1.0",
        resourceType=ResourceType.Workspace,
        current=True,
        required=[],
        properties={},
        customActions=[],
    ).model_dump()

    template = await resource_repo.validate_input_against_template(
        "template1", workspace_input, ResourceType.Workspace, ["test_user_role"]
    )

    # does not throw
    assert template.version == "0.1.0"


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
async def test_validate_input_against_nested_template_missing_nested_prop(enriched_template_mock, resource_repo):
    enriched_template_mock.return_value = sample_nested_template()
    # missing port
    nested_input = WorkspaceInCreate(templateName="template1")
    nested_input.properties["rules"] = [{"protocol": {"method": "post"}}]

    with pytest.raises(ValidationError):
        await resource_repo.validate_input_against_template("template1", nested_input, ResourceType.Workspace)


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
async def test_validate_input_against_nested_template_valid(enriched_template_mock, resource_repo):
    enriched_template_mock.return_value = sample_nested_template()

    # has required props, nested
    nested_input = WorkspaceInCreate(templateName="template1")
    nested_input.properties["rules"] = [{"protocol": {"method": "post", "port": "1234"}}]

    resp_template = await resource_repo.validate_input_against_template(
        "template1", nested_input, ResourceType.Workspace
    )
    assert resp_template is not None


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceTemplateRepository.get_current_template")
async def test_get_enriched_template_returns_the_enriched_template(get_current_mock, resource_repo):
    workspace_template = ResourceTemplate(
        id="abc",
        name="template1",
        description="",
        version="",
        resourceType=ResourceType.Workspace,
        current=True,
        required=[],
        properties={},
        customActions=[],
    )
    get_current_mock.return_value = workspace_template

    template = await resource_repo._get_enriched_template("template1", ResourceType.Workspace)

    get_current_mock.assert_called_once_with("template1", ResourceType.Workspace, "")
    assert "display_name" in template["properties"]


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceTemplateRepository.get_current_template")
async def test_get_enriched_template_returns_the_enriched_template_for_user_resources(get_current_mock, resource_repo):
    user_resource_template = UserResourceTemplate(
        id="abc",
        name="template1",
        description="",
        version="",
        resourceType=ResourceType.Workspace,
        current=True,
        required=[],
        properties={},
        customActions=[],
        parentWorkspaceService="parent-template1",
    )
    get_current_mock.return_value = user_resource_template

    template = await resource_repo._get_enriched_template("template1", ResourceType.UserResource, "parent-template1")

    get_current_mock.assert_called_once_with("template1", ResourceType.UserResource, "parent-template1")
    assert "display_name" in template["properties"]


@pytest.mark.asyncio
async def test_get_resource_dict_by_id_raises_entity_does_not_exist_if_no_resources_come_back(resource_repo):
    item_id = "123"
    resource_repo.read_item_by_id = AsyncMock(side_effect=CosmosResourceNotFoundError)

    with pytest.raises(EntityDoesNotExist):
        await resource_repo.get_resource_dict_by_id(item_id)


@pytest.mark.asyncio
@patch("db.repositories.resources_history.ResourceHistoryRepository.save_item", return_value=AsyncMock())
@patch("db.repositories.resources.ResourceRepository.validate_patch")
@patch("db.repositories.resources.ResourceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
async def test_patch_resource_preserves_property_history(
    _, __, ___, resource_repo, resource_history_repo, basic_resource_template
):
    """
    Tests that properties are copied into a history array and only certain values in the root are updated
    """

    resource_repo.update_item_with_etag = AsyncMock(return_value=None)
    resource_patch = ResourcePatch(isEnabled=True, properties={"display_name": "updated name"})

    etag = "some-etag-value"
    user = create_test_user()

    resource = sample_resource()
    expected_resource = sample_resource()
    expected_resource.properties["display_name"] = "updated name"
    expected_resource.resourceVersion = 1
    expected_resource.user = user.model_dump()
    expected_resource.updatedWhen = FAKE_UPDATE_TIMESTAMP

    await resource_repo.patch_resource(
        resource,
        resource_patch,
        basic_resource_template,
        etag,
        None,
        resource_history_repo,
        user,
        strings.RESOURCE_ACTION_UPDATE,
    )
    resource_repo.update_item_with_etag.assert_called_once_with(expected_resource, etag)

    # now patch again
    new_resource = copy.deepcopy(expected_resource)  # new_resource is after the first patch
    new_patch = ResourcePatch(isEnabled=False, properties={"display_name": "updated name 2"})
    expected_resource.resourceVersion = 2
    expected_resource.properties["display_name"] = "updated name 2"
    expected_resource.isEnabled = False
    expected_resource.user = user.model_dump()

    await resource_repo.patch_resource(
        new_resource,
        new_patch,
        basic_resource_template,
        etag,
        None,
        resource_history_repo,
        user,
        strings.RESOURCE_ACTION_UPDATE,
    )
    resource_repo.update_item_with_etag.assert_called_with(expected_resource, etag)


def template_with_secret(template: ResourceTemplate) -> ResourceTemplate:
    template = template.model_copy(deep=True)
    template.properties["client_secret"] = {"type": "string", "sensitive": True, "updateable": True}
    return template


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository.validate_patch")
@patch("db.repositories.resources.ResourceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
async def test_patch_resource_stores_a_placeholder_for_sensitive_values(_, __, resource_repo, basic_resource_template):
    resource_repo.update_item_with_etag = AsyncMock()
    history_repo = AsyncMock()
    resource = sample_resource()
    # A document that an update wrote before the update path masked sensitive values.
    resource.properties["client_secret"] = "earlier value"
    resource_patch = ResourcePatch(properties={"client_secret": "new value"})

    returned, _ = await resource_repo.patch_resource(
        resource,
        resource_patch,
        template_with_secret(basic_resource_template),
        "etag",
        None,
        history_repo,
        create_test_user(),
        strings.RESOURCE_ACTION_UPDATE,
    )

    stored = resource_repo.update_item_with_etag.await_args.args[0]
    assert stored.properties["client_secret"] == strings.REDACTED_SENSITIVE_VALUE
    assert stored.properties["display_name"] == "initial display name"
    # The caller builds the request message from the returned resource.
    assert returned.properties["client_secret"] == "new value"
    history_item = history_repo.create_resource_history_item.await_args.args[0]
    assert history_item.properties["client_secret"] == strings.REDACTED_SENSITIVE_VALUE


def stored_resource(resource_id, template_name, resource_type, properties, **fields):
    return {
        "id": resource_id,
        "templateName": template_name,
        "templateVersion": "1.0.0",
        "resourceType": resource_type,
        "properties": properties,
        **fields,
    }


@pytest.mark.asyncio
async def test_mask_stored_sensitive_values_replaces_only_real_values(resource_repo, basic_resource_template):
    template = template_with_secret(basic_resource_template)
    resource_repo._container = AsyncMock()
    resource_repo.query = AsyncMock(
        return_value=[
            stored_resource("ws", "workspace-template", "workspace", {"client_secret": "real", "display_name": "n"}),
            stored_resource("ws-2", "workspace-template", "workspace", {"client_secret": "REDACTED"}),
            stored_resource("svc", "service-template", "workspace-service", {}),
            stored_resource(
                "ur", "user-template", "user-resource", {"client_secret": "real"}, parentWorkspaceServiceId="svc"
            ),
            stored_resource("old", "removed-template", "workspace", {"client_secret": "real"}),
        ]
    )

    async def get_template(name, version, resource_type, parent_service_name=None):
        if name == "removed-template":
            raise EntityDoesNotExist
        return template

    secret = {"properties": {"client_secret": {"type": "string", "sensitive": True}}}
    template_repo = AsyncMock()
    template_repo.get_template_by_name_and_version.side_effect = get_template
    template_repo.query.return_value = [
        {"name": "workspace-template", **secret},
        {"name": "user-template", **secret},
        {"name": "removed-template", **secret},
        {"name": "service-template", "properties": {"display_name": {"type": "string"}}},
    ]
    history = {
        "ws": [
            {"id": "h-1", "resourceId": "ws", "templateVersion": "0.9.0", "properties": {"client_secret": "older"}},
            {"id": "h-2", "resourceId": "ws", "properties": {"client_secret": "REDACTED"}},
        ],
    }

    async def history_query(query, parameters):
        return history.get(parameters[0]["value"], [])

    history_repo = MagicMock()
    history_repo.container = AsyncMock()
    history_repo.query = AsyncMock(side_effect=history_query)

    result = await resource_repo.mask_stored_sensitive_values(template_repo, history_repo)

    assert result == (2, 1)
    set_secret = [{"op": "set", "path": "/properties/client_secret", "value": strings.REDACTED_SENSITIVE_VALUE}]
    assert [call.kwargs for call in resource_repo.container.patch_item.await_args_list] == [
        {"item": "ws", "partition_key": "ws", "patch_operations": set_secret},
        {"item": "ur", "partition_key": "ur", "patch_operations": set_secret},
    ]
    # The history container uses the resource ID as its partition key.
    history_repo.container.patch_item.assert_awaited_once_with(
        item="h-1", partition_key="ws", patch_operations=set_secret
    )
    # A resource of a template without a sensitive property needs no history read.
    read_ids = [call.kwargs["parameters"][0]["value"] for call in history_repo.query.await_args_list]
    assert read_ids == ["ws", "ws-2", "ur", "old"]
    template_repo.get_template_by_name_and_version.assert_any_await(
        "user-template", "1.0.0", ResourceType.UserResource, "service-template"
    )
    template_repo.get_template_by_name_and_version.assert_any_await(
        "workspace-template", "0.9.0", ResourceType.Workspace, None
    )


SECRET = {"type": "string", "sensitive": True}
ACCOUNTS = {
    "accounts": {
        "type": "array",
        "updateable": True,
        "items": {"type": "object", "properties": {"name": {"type": "string"}, "token": SECRET}},
    }
}


def masking_template(properties, all_of=None) -> ResourceTemplate:
    return ResourceTemplate(
        id="masking-template-id",
        name="masking-template",
        version="1.0.0",
        resourceType=ResourceType.Workspace,
        current=True,
        required=[],
        properties=properties,
        allOf=all_of,
    )


def test_masked_property_paths_escape_nested_names():
    template = masking_template({"settings": {"type": "object", "properties": {"a/b": SECRET, "c~d": SECRET}}})
    properties = {"settings": {"a/b": "real", "c~d": "real", "plain": "x"}}

    assert masked_property_paths(properties, template) == ["/properties/settings/a~1b", "/properties/settings/c~0d"]


@pytest.mark.asyncio
async def test_set_masked_values_sends_at_most_ten_operations_in_each_request():
    container = AsyncMock()
    paths = [f"/properties/secret_{index}" for index in range(11)]

    await set_masked_values(container, "item", "partition", paths)

    assert [len(call.kwargs["patch_operations"]) for call in container.patch_item.await_args_list] == [10, 1]


PASSWORD = {"type": "string", "sensitive": True, "updateable": True}
PASSWORD_RULE = {"properties": {"password": {"type": "string", "pattern": "^.{8,}$"}}}
IF_MODE_A = {"properties": {"mode": {"const": "a"}}}


@pytest.mark.parametrize(
    "properties, all_of",
    [
        ({"password": PASSWORD}, [{"if": IF_MODE_A, "then": PASSWORD_RULE}]),
        ({"password": PASSWORD}, [{"if": IF_MODE_A, "then": {}, "else": PASSWORD_RULE}]),
        ({"password": PASSWORD}, [{"anyOf": [PASSWORD_RULE]}]),
        ({"password": PASSWORD}, [{"oneOf": [PASSWORD_RULE, {}]}]),
        (
            {"password": {"type": "string"}},
            [
                {"if": IF_MODE_A, "then": {"properties": {"password": PASSWORD}}},
                {"if": IF_MODE_A, "then": PASSWORD_RULE},
            ],
        ),
    ],
)
def test_a_property_stays_sensitive_if_one_of_its_declarations_is_sensitive(properties, all_of):
    # A later declaration of the same name without the flag must not remove it.
    masked = mask_sensitive_properties({"password": "real value", "mode": "a"}, masking_template(properties, all_of))

    assert masked == {"password": strings.REDACTED_SENSITIVE_VALUE, "mode": "a"}


def history_without_items():
    history_repo = MagicMock()
    history_repo.container = AsyncMock()
    history_repo.query = AsyncMock(return_value=[])
    return history_repo


@pytest.mark.asyncio
async def test_mask_stored_sensitive_values_finds_a_property_that_a_branch_declares_again(resource_repo):
    template = masking_template({"password": PASSWORD}, [{"if": IF_MODE_A, "then": PASSWORD_RULE}])
    resource_repo._container = AsyncMock()
    resource_repo.query = AsyncMock(
        return_value=[stored_resource("ws", "masking-template", "workspace", {"password": "real"})]
    )
    template_repo = AsyncMock()
    template_repo.query.return_value = [template.model_dump()]
    template_repo.get_template_by_name_and_version.return_value = template

    assert await resource_repo.mask_stored_sensitive_values(template_repo, history_without_items()) == (1, 0)
    resource_repo.container.patch_item.assert_awaited_once_with(
        item="ws",
        partition_key="ws",
        patch_operations=[{"op": "set", "path": "/properties/password", "value": strings.REDACTED_SENSITIVE_VALUE}],
    )


def test_the_migration_finds_the_values_that_an_install_or_an_update_masks():
    template = masking_template({**ACCOUNTS, "settings": {"type": "object", "properties": {"password": SECRET}}})
    properties = {
        "accounts": [{"name": "a", "token": "first"}, {"name": "b", "token": strings.REDACTED_SENSITIVE_VALUE}],
        "groups": [[{"token": "nested"}]],
        "settings": {"password": "real", "name": "token"},
    }

    assert mask_sensitive_properties(properties, template) == {
        "accounts": [
            {"name": "a", "token": strings.REDACTED_SENSITIVE_VALUE},
            {"name": "b", "token": strings.REDACTED_SENSITIVE_VALUE},
        ],
        "groups": [[{"token": strings.REDACTED_SENSITIVE_VALUE}]],
        "settings": {"password": strings.REDACTED_SENSITIVE_VALUE, "name": "token"},
    }
    # The migration changes only the values that are not the placeholder yet, and not a whole list.
    assert masked_property_paths(properties, template) == [
        "/properties/accounts/0/token",
        "/properties/groups/0/0/token",
        "/properties/settings/password",
    ]


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository.validate_patch")
@patch("db.repositories.resources.ResourceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
async def test_patch_resource_stores_a_placeholder_for_sensitive_values_in_array_items(_, __, resource_repo):
    resource_repo.update_item_with_etag = AsyncMock()
    history_repo = AsyncMock()
    resource = sample_resource()
    resource.properties["accounts"] = [{"name": "a", "token": "earlier value"}]
    resource_patch = ResourcePatch(properties={"accounts": [{"name": "a", "token": "new value"}]})

    returned, _ = await resource_repo.patch_resource(
        resource,
        resource_patch,
        masking_template(ACCOUNTS),
        "etag",
        None,
        history_repo,
        create_test_user(),
        strings.RESOURCE_ACTION_UPDATE,
    )

    masked_accounts = [{"name": "a", "token": strings.REDACTED_SENSITIVE_VALUE}]
    assert resource_repo.update_item_with_etag.await_args.args[0].properties["accounts"] == masked_accounts
    assert returned.properties["accounts"] == [{"name": "a", "token": "new value"}]
    assert history_repo.create_resource_history_item.await_args.args[0].properties["accounts"] == masked_accounts


@pytest.mark.asyncio
async def test_mask_stored_sensitive_values_masks_values_in_array_items(resource_repo):
    template = masking_template(ACCOUNTS)
    resource_repo._container = AsyncMock()
    accounts = [{"name": "a", "token": "real"}, {"name": "b", "token": strings.REDACTED_SENSITIVE_VALUE}]
    resource_repo.query = AsyncMock(
        return_value=[stored_resource("ws", "masking-template", "workspace", {"accounts": accounts})]
    )
    template_repo = AsyncMock()
    template_repo.query.return_value = [template.model_dump()]
    template_repo.get_template_by_name_and_version.return_value = template
    history_repo = history_without_items()
    history_repo.query.return_value = [{"id": "h-1", "resourceId": "ws", "properties": {"accounts": accounts[:1]}}]

    assert await resource_repo.mask_stored_sensitive_values(template_repo, history_repo) == (1, 1)
    set_token = [{"op": "set", "path": "/properties/accounts/0/token", "value": strings.REDACTED_SENSITIVE_VALUE}]
    resource_repo.container.patch_item.assert_awaited_once_with(
        item="ws", partition_key="ws", patch_operations=set_token
    )
    history_repo.container.patch_item.assert_awaited_once_with(
        item="h-1", partition_key="ws", patch_operations=set_token
    )


def test_restore_sensitive_values_restores_values_in_array_items():
    # A pipeline step of the primary resource reads the stored document and gets the real values from memory.
    placeholder = {"token": strings.REDACTED_SENSITIVE_VALUE}
    stored = {"accounts": [{"name": "a", **placeholder}, {"name": "b", **placeholder}], "groups": [placeholder]}
    source = {
        "accounts": [{"name": "a", "token": "first"}, {"name": "b", "token": "second"}],
        "groups": [{"token": "x"}, {"token": "y"}],
    }

    restored = restore_sensitive_values(stored, source)

    assert restored["accounts"] == source["accounts"]
    # The items of two lists with different lengths can be different items, so the placeholder stays.
    assert restored["groups"] == [placeholder]


@patch("db.repositories.resources.ResourceTemplateRepository.enrich_template")
def test_validate_patch_with_good_fields_passes(template_repo, resource_repo):
    """
    Make sure that patch is NOT valid when non-updateable fields are included
    """

    template_repo.enrich_template = MagicMock(return_value=sample_resource_template())
    template = sample_resource_template()

    # check it's valid when updating a single updateable prop
    patch = ResourcePatch(isEnabled=True, properties={"vm_size": "large"})
    resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)


@patch("db.repositories.resources.ResourceTemplateRepository.enrich_template")
def test_validate_patch_with_bad_fields_fails(template_repo, resource_repo):
    """
    Make sure that patch is NOT valid when non-updateable fields are included
    """

    template_repo.enrich_template = MagicMock(return_value=sample_resource_template())
    template = sample_resource_template()

    # check it's invalid when sending an unexpected field
    patch = ResourcePatch(isEnabled=True, properties={"vm_size": "large", "unexpected_field": "surprise!"})
    with pytest.raises(ValidationError):
        resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_INSTALL)

    # check it's invalid when sending a bad value
    patch = ResourcePatch(isEnabled=True, properties={"vm_size": "huge"})
    with pytest.raises(ValidationError):
        resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_INSTALL)

    # check it's invalid when trying to update a non-updateable field
    patch = ResourcePatch(isEnabled=True, properties={"vm_size": "large", "os_image": "linux"})
    with pytest.raises(ValidationError):
        resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_INSTALL)


@pytest.mark.parametrize(
    "nested_schema_id",
    [
        "#/properties/guac_disable_paste",
        "#properties/network_rule_collections",
        "https://example.com/template_schema.json#properties/network_rule_collections",
    ],
)
def test_validate_resource_parameters_ignores_legacy_nested_schema_ids(resource_repo, nested_schema_id):
    template = {
        "$id": "https://example.com/template_schema.json",
        "type": "object",
        "required": ["network_rule_collections"],
        "properties": {"network_rule_collections": {"$id": nested_schema_id, "type": "array"}},
    }

    resource_input = {"properties": {"network_rule_collections": []}}

    # Should not raise SchemaError from jsonschema's metaschema checks.
    resource_repo._validate_resource_parameters(resource_input, template)

    # Normalization must not mutate stored templates or remove root metadata.
    normalized_template = resource_repo._normalize_template_schema(template)
    assert normalized_template["$id"] == template["$id"]
    assert "$id" not in normalized_template["properties"]["network_rule_collections"]
    assert template["properties"]["network_rule_collections"]["$id"] == nested_schema_id


def test_validate_resource_parameters_ignores_invalid_const_null_on_non_nullable_property(resource_repo):
    template = {
        "$id": "https://example.com/template_schema.json",
        "type": "object",
        "required": ["storage_account_redundancy"],
        "properties": {"storage_account_redundancy": {"type": "string", "enum": ["GRS", "ZRS"], "const": None}},
    }

    resource_input = {"properties": {"storage_account_redundancy": "GRS"}}

    # Should not raise because const:null is incompatible with this non-nullable property.
    resource_repo._validate_resource_parameters(resource_input, template)

    normalized_template = resource_repo._normalize_template_schema(template)
    assert "const" not in normalized_template["properties"]["storage_account_redundancy"]
    assert template["properties"]["storage_account_redundancy"]["const"] is None


def test_validate_resource_parameters_keeps_nullable_const_null(resource_repo):
    template = {
        "$id": "https://example.com/template_schema.json",
        "type": "object",
        "required": ["nullable_const"],
        "properties": {"nullable_const": {"const": None}},
    }

    resource_input = {"properties": {"nullable_const": None}}

    # Explicit nullable const usage should still validate and remain in schema.
    resource_repo._validate_resource_parameters(resource_input, template)

    normalized_template = resource_repo._normalize_template_schema(template)
    assert normalized_template["properties"]["nullable_const"]["const"] is None
