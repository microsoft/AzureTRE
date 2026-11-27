import copy
from unittest.mock import AsyncMock
import uuid
import pytest
import pytest_asyncio
from mock import patch, MagicMock
from pydantic import TypeAdapter

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
    sensitive_schema,
)
from azure.core import MatchConditions
from azure.cosmos.exceptions import (
    CosmosAccessConditionFailedError,
    CosmosHttpResponseError,
    CosmosResourceNotFoundError,
)
from models.domain.resource import Resource
from models.domain.resource_template import ResourceTemplate
from models.domain.user_resource import UserResource
from models.domain.user_resource_template import UserResourceTemplate
from models.domain.workspace import ResourceType
from models.schemas.resource import ResourcePatch
from models.schemas.workspace import WorkspaceInCreate


RESOURCE_ID = str(uuid.uuid4())


def parse_obj_as(model_type, value):
    return TypeAdapter(model_type).validate_python(value)


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
                "enum": ["Windows 11", "Windows Server 2025"],
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


def test_validate_resource_parameters_ignores_template_document_id():
    resource_input = {"properties": {"title": "test", "os_image": "Windows 11"}}

    ResourceRepository._validate_resource_parameters(resource_input, sample_resource_template())


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
        required=["os_image", "title"],
        properties={
            "title": {"type": "string", "title": "Title of the resource"},
            "os_image": {
                "type": "string",
                "title": "Windows image",
                "description": "Select Windows image to use for VM",
                "enum": ["Windows 11", "Windows Server 2025"],
                "updateable": False,
            },
            "vm_size": {
                "type": "string",
                "title": "VM Size",
                "description": "Select Windows image to use for VM",
                "enum": ["small", "large"],
                "updateable": True,
            },
            "new_property": {
                "type": "string",
                "title": "New non-updateable property",
                "enum": ["value1", "value2"],
                "updateable": False,
            },
        },
        actions=[],
    ).model_dump(exclude_none=True)


def test_matches_if_condition_requires_referenced_properties(resource_repo):
    assert not resource_repo._matches_if_condition(
        {"properties": {"selector": {"const": "A"}}},
        {},
    )
    assert not resource_repo._matches_if_condition(
        {"properties": {"selector": {"enum": [None, "A"]}}},
        {},
    )
    assert resource_repo._matches_if_condition(
        {"properties": {"selector": {"const": None}}},
        {"selector": None},
    )


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

    # the enrich template method does this
    template_dict["allOf"] = None
    template_dict.pop("allOf")

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
        "_etag": "1",
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
            {
                "id": "h-1",
                "resourceId": "ws",
                "templateVersion": "0.9.0",
                "properties": {"client_secret": "older"},
                "_etag": "1",
            },
            {"id": "h-2", "resourceId": "ws", "properties": {"client_secret": "REDACTED"}, "_etag": "1"},
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
    if_not_modified = {"etag": "1", "match_condition": MatchConditions.IfNotModified}
    assert [call.kwargs for call in resource_repo.container.patch_item.await_args_list] == [
        {"item": "ws", "partition_key": "ws", "patch_operations": set_secret, **if_not_modified},
        {"item": "ur", "partition_key": "ur", "patch_operations": set_secret, **if_not_modified},
    ]
    # The history container uses the resource ID as its partition key.
    history_repo.container.patch_item.assert_awaited_once_with(
        item="h-1", partition_key="ws", patch_operations=set_secret, **if_not_modified
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


def masking_template(properties, all_of=None, version="1.0.0", defs=None) -> ResourceTemplate:
    return ResourceTemplate(
        id="masking-template-id",
        name="masking-template",
        version=version,
        resourceType=ResourceType.Workspace,
        current=True,
        required=[],
        properties=properties,
        allOf=all_of,
        defs=defs,
    )


def test_masked_property_paths_escape_nested_names():
    template = masking_template({"settings": {"type": "object", "properties": {"a/b": SECRET, "c~d": SECRET}}})
    properties = {"settings": {"a/b": "real", "c~d": "real", "plain": "x"}}

    assert masked_property_paths(properties, template) == ["/properties/settings/a~1b", "/properties/settings/c~0d"]


class FakeContainer:
    """Apply a patch with an etag only to the document that has this etag, as Cosmos DB does."""

    def __init__(self, *documents):
        self.documents = {document["id"]: copy.deepcopy(document) for document in documents}
        self.requests = []

    async def read_item(self, item, partition_key):
        return copy.deepcopy(self.documents[item])

    async def patch_item(self, item, partition_key, patch_operations, etag=None, match_condition=None):
        self.requests.append((item, len(patch_operations), etag))
        document = copy.deepcopy(self.documents[item])
        if match_condition == MatchConditions.IfNotModified and etag != document["_etag"]:
            raise CosmosAccessConditionFailedError(status_code=412)
        for operation in patch_operations:
            *parents, name = [part.replace("~1", "/").replace("~0", "~") for part in operation["path"].split("/")[1:]]
            target = document
            try:
                for part in parents:
                    target = target[int(part)] if isinstance(target, list) else target[part]
                target[int(name) if isinstance(target, list) else name] = operation["value"]
            except (IndexError, KeyError):
                raise CosmosHttpResponseError(status_code=400, message=f"The path {operation['path']} does not exist")
        document["_etag"] = str(int(document["_etag"]) + 1)
        self.documents[item] = document
        return copy.deepcopy(document)


def migration_template_repo(*templates):
    template_repo = AsyncMock()
    template_repo.query.return_value = [template.model_dump() for template in templates]
    by_version = {template.version: template for template in templates}
    template_repo.get_template_by_name_and_version.side_effect = lambda name, version, *_: by_version[version]
    return template_repo


@pytest.mark.asyncio
async def test_the_migration_sends_at_most_ten_operations_with_the_etag_of_each_result(resource_repo):
    secrets = {f"secret_{index}": SECRET for index in range(11)}
    snapshot = stored_resource("ws", "masking-template", "workspace", {name: "real" for name in secrets})
    resource_repo._container = FakeContainer(snapshot)
    resource_repo.query = AsyncMock(return_value=[snapshot])

    result = await resource_repo.mask_stored_sensitive_values(
        migration_template_repo(masking_template(secrets)), history_without_items()
    )

    assert result == (1, 0)
    # Cosmos DB accepts at most 10 operations in one request. The second request has the etag of the first result.
    assert resource_repo.container.requests == [("ws", 10, "1"), ("ws", 1, "2")]
    assert set(resource_repo.container.documents["ws"]["properties"].values()) == {strings.REDACTED_SENSITIVE_VALUE}


@pytest.mark.asyncio
async def test_the_migration_keeps_a_new_value_that_the_new_version_does_not_mark_sensitive(resource_repo):
    first = masking_template({"token": SECRET})
    second = masking_template({"token": {"type": "string"}}, version="2.0.0")
    snapshot = stored_resource("ws", "masking-template", "workspace", {"token": "earlier value"})
    # After the read of the migration, an update set a new value and a version that does not mark it sensitive.
    updated = {**snapshot, "templateVersion": "2.0.0", "properties": {"token": "new value"}, "_etag": "2"}
    resource_repo._container = FakeContainer(updated)
    resource_repo.query = AsyncMock(return_value=[snapshot])

    result = await resource_repo.mask_stored_sensitive_values(
        migration_template_repo(first, second), history_without_items()
    )

    assert result == (0, 0)
    assert resource_repo.container.documents["ws"]["properties"] == {"token": "new value"}


@pytest.mark.asyncio
async def test_the_migration_computes_the_paths_again_after_a_change_and_continues(resource_repo):
    accounts = [{"name": "a", "token": "real"}, {"name": "b", "token": "real"}]
    snapshot = [
        stored_resource("ws", "masking-template", "workspace", {"accounts": accounts}),
        stored_resource("ws-2", "masking-template", "workspace", {"accounts": accounts[:1]}),
    ]
    # After the read of the migration, an update removed the second account. The path with index 1 is not valid now.
    updated = {**snapshot[0], "properties": {"accounts": accounts[:1]}, "_etag": "2"}
    resource_repo._container = FakeContainer(updated, snapshot[1])
    resource_repo.query = AsyncMock(return_value=snapshot)

    result = await resource_repo.mask_stored_sensitive_values(
        migration_template_repo(masking_template(ACCOUNTS)), history_without_items()
    )

    assert result == (2, 0)
    assert resource_repo.container.requests == [("ws", 2, "1"), ("ws", 1, "2"), ("ws-2", 1, "1")]
    masked = [{"name": "a", "token": strings.REDACTED_SENSITIVE_VALUE}]
    documents = resource_repo.container.documents
    assert [documents[resource_id]["properties"]["accounts"] for resource_id in ("ws", "ws-2")] == [masked] * 2


@pytest.mark.asyncio
async def test_the_migration_continues_if_a_document_changes_at_each_attempt(resource_repo):
    class BusyContainer(FakeContainer):
        async def patch_item(self, item, **kwargs):
            if item == "ws":
                # Another request changes the document before each patch of the migration.
                self.documents[item]["_etag"] = str(int(self.documents[item]["_etag"]) + 1)
            return await super().patch_item(item, **kwargs)

    snapshot = [
        stored_resource("ws", "masking-template", "workspace", {"token": "real"}),
        stored_resource("ws-2", "masking-template", "workspace", {"token": "real"}),
    ]
    resource_repo._container = BusyContainer(*snapshot)
    resource_repo.query = AsyncMock(return_value=snapshot)

    with patch("db.repositories.resources.logger") as logger:
        result = await resource_repo.mask_stored_sensitive_values(
            migration_template_repo(masking_template({"token": SECRET})), history_without_items()
        )

    assert result == (1, 0)
    assert [request[0] for request in resource_repo.container.requests] == ["ws", "ws", "ws", "ws-2"]
    assert resource_repo.container.documents["ws"]["properties"] == {"token": "real"}
    assert resource_repo.container.documents["ws-2"]["properties"] == {"token": strings.REDACTED_SENSITIVE_VALUE}
    logger.warning.assert_called_once()


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
        etag="1",
        match_condition=MatchConditions.IfNotModified,
    )


GROUPS = {
    "groups": {
        "type": "array",
        "items": {"type": "array", "items": {"type": "object", "properties": {"token": SECRET}}},
    }
}


def test_the_migration_finds_the_values_that_an_install_or_an_update_masks():
    template = masking_template(
        {**ACCOUNTS, **GROUPS, "settings": {"type": "object", "properties": {"password": SECRET}}}
    )
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


def test_a_key_with_the_name_of_a_sensitive_property_at_another_path_keeps_its_value():
    # A later action reads the stored copy, so a value that is not sensitive must stay real.
    template = masking_template(
        {
            "password": SECRET,
            "settings": {"type": "object", "properties": {"password": {"type": "string"}}},
            **ACCOUNTS,
        }
    )
    properties = {
        "password": "real",
        "settings": {"password": "not sensitive", "token": "not declared"},
        "accounts": [{"name": "a", "token": "real", "password": "not declared"}],
        "token": "not declared",
    }

    assert mask_sensitive_properties(properties, template) == {
        "password": strings.REDACTED_SENSITIVE_VALUE,
        "settings": {"password": "not sensitive", "token": "not declared"},
        "accounts": [{"name": "a", "token": strings.REDACTED_SENSITIVE_VALUE, "password": "not declared"}],
        "token": "not declared",
    }
    assert masked_property_paths(properties, template) == ["/properties/password", "/properties/accounts/0/token"]


def test_a_branch_can_declare_a_nested_property_as_sensitive():
    template = masking_template(
        {"settings": {"type": "object", "properties": {"password": {"type": "string"}}}},
        [{"if": IF_MODE_A, "then": {"properties": {"settings": {"properties": {"password": SECRET}}}}}],
    )

    masked = mask_sensitive_properties({"mode": "a", "settings": {"password": "real", "name": "x"}}, template)

    assert masked == {"mode": "a", "settings": {"password": strings.REDACTED_SENSITIVE_VALUE, "name": "x"}}


def test_a_definition_that_a_ref_points_to_can_declare_a_sensitive_property():
    template = masking_template(
        {
            "login": {"$ref": "#/$defs/credentials"},
            "api_key": {"$ref": "#/$defs/secret"},
            "settings": {"type": "object", "properties": {"password": {"type": "string"}}},
        },
        defs={
            "credentials": {"type": "object", "properties": {"user": {"type": "string"}, "password": SECRET}},
            "secret": SECRET,
        },
    )
    properties = {"login": {"user": "u", "password": "real"}, "api_key": "real", "settings": {"password": "x"}}

    assert mask_sensitive_properties(properties, template) == {
        "login": {"user": "u", "password": strings.REDACTED_SENSITIVE_VALUE},
        "api_key": strings.REDACTED_SENSITIVE_VALUE,
        "settings": {"password": "x"},
    }


def test_a_recursive_definition_with_a_sensitive_property_masks_the_value_where_it_repeats():
    node = {"type": "object", "properties": {"name": {"type": "string"}, "child": {"$ref": "#/$defs/node"}}}
    secret_node = {"type": "object", "properties": {"token": SECRET, "child": {"$ref": "#/$defs/secret_node"}}}
    template = masking_template(
        {"tree": {"$ref": "#/$defs/node"}, "vault": {"$ref": "#/$defs/secret_node"}},
        defs={"node": node, "secret_node": secret_node},
    )
    properties = {"tree": {"name": "a", "child": {"name": "b"}}, "vault": {"token": "real", "child": {"token": "real"}}}

    assert mask_sensitive_properties(properties, template) == {
        "tree": {"name": "a", "child": {"name": "b"}},
        "vault": {"token": strings.REDACTED_SENSITIVE_VALUE, "child": strings.REDACTED_SENSITIVE_VALUE},
    }


R = strings.REDACTED_SENSITIVE_VALUE
NAME = {"name": {"type": "string"}}
TOKEN_OBJECT = {"type": "object", "properties": {"label": {"type": "string"}, "token": SECRET}}


@pytest.mark.parametrize(
    "declaration, value, masked",
    [
        # A key that properties does not name gets the declaration of additionalProperties.
        (
            {"type": "object", "properties": NAME, "additionalProperties": TOKEN_OBJECT},
            {"name": "n", "a": {"label": "l", "token": "real"}},
            {"name": "n", "a": {"label": "l", "token": R}},
        ),
        (
            {"type": "object", "properties": NAME, "additionalProperties": SECRET},
            {"name": "n", "a": "real"},
            {"name": "n", "a": R},
        ),
        # A key gets the declaration of each pattern that it matches.
        (
            {"type": "object", "patternProperties": {"^key_": SECRET}},
            {"key_a": "real", "b": "x"},
            {"key_a": R, "b": "x"},
        ),
        (
            {"type": "object", "patternProperties": {"^a": TOKEN_OBJECT}},
            {"a1": {"label": "l", "token": "real"}},
            {"a1": {"label": "l", "token": R}},
        ),
        # A list item gets the declaration at its index, and the items after the prefix get the rest.
        ({"type": "array", "prefixItems": [{"type": "string"}, SECRET]}, ["x", "real"], ["x", R]),
        ({"type": "array", "prefixItems": [{"type": "string"}], "items": SECRET}, ["x", "real", "real"], ["x", R, R]),
        # A declaration that depends on another key describes the same object.
        (
            {"type": "object", "properties": NAME, "dependentSchemas": {"name": {"properties": {"token": SECRET}}}},
            {"name": "n", "token": "real"},
            {"name": "n", "token": R},
        ),
        # unevaluatedProperties and unevaluatedItems use the same rule as additionalProperties and items.
        (
            {"type": "object", "properties": NAME, "unevaluatedProperties": SECRET},
            {"name": "n", "a": "real"},
            {"name": "n", "a": R},
        ),
        ({"type": "array", "prefixItems": [{"type": "string"}], "unevaluatedItems": SECRET}, ["x", "real"], ["x", R]),
        # A path cannot name the item that contains describes, so each item is masked.
        ({"type": "array", "contains": SECRET}, ["x", "real"], [R, R]),
    ],
)
def test_each_schema_keyword_that_describes_a_value_can_declare_it_as_sensitive(declaration, value, masked):
    template = masking_template({"setting": declaration})

    assert mask_sensitive_properties({"setting": value}, template) == {"setting": masked}
    # The migration selects the templates to read with the same function.
    assert sensitive_schema(template.model_dump())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "all_of, masked",
    [
        (
            [{"properties": NAME, "unevaluatedProperties": TOKEN_OBJECT}],
            {"name": "n", "settings": {"label": "l", "token": R}},
        ),
        # A sensitive flag at the top level masks each property, and the properties stay an object.
        ([{"sensitive": True}], {"name": R, "settings": R}),
    ],
)
async def test_a_sensitive_flag_in_a_top_level_branch_keeps_the_properties_an_object(resource_repo, all_of, masked):
    template = masking_template({**NAME, "settings": {"type": "object"}}, all_of)
    properties = {"name": "n", "settings": {"label": "l", "token": "real"}}
    snapshot = stored_resource("ws", "masking-template", "workspace", copy.deepcopy(properties))
    resource_repo._container = FakeContainer(snapshot)
    resource_repo.query = AsyncMock(return_value=[snapshot])

    assert mask_sensitive_properties(properties, template) == masked
    assert await resource_repo.mask_stored_sensitive_values(
        migration_template_repo(template), history_without_items()
    ) == (1, 0)
    assert resource_repo.container.documents["ws"]["properties"] == masked


def test_each_item_of_a_list_with_sensitive_items_is_masked():
    template = masking_template({"keys": {"type": "array", "items": SECRET}})

    assert mask_sensitive_properties({"keys": ["a", "b"]}, template) == {
        "keys": [strings.REDACTED_SENSITIVE_VALUE, strings.REDACTED_SENSITIVE_VALUE]
    }
    assert masked_property_paths({"keys": ["a", strings.REDACTED_SENSITIVE_VALUE]}, template) == ["/properties/keys/0"]


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
    history_repo.query.return_value = [
        {"id": "h-1", "resourceId": "ws", "properties": {"accounts": accounts[:1]}, "_etag": "1"}
    ]

    assert await resource_repo.mask_stored_sensitive_values(template_repo, history_repo) == (1, 1)
    set_token = [{"op": "set", "path": "/properties/accounts/0/token", "value": strings.REDACTED_SENSITIVE_VALUE}]
    if_not_modified = {"etag": "1", "match_condition": MatchConditions.IfNotModified}
    resource_repo.container.patch_item.assert_awaited_once_with(
        item="ws", partition_key="ws", patch_operations=set_token, **if_not_modified
    )
    history_repo.container.patch_item.assert_awaited_once_with(
        item="h-1", partition_key="ws", patch_operations=set_token, **if_not_modified
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


def test_restore_sensitive_values_restores_an_explicit_null():
    # The install stores a placeholder also for a null value. Only a key that the request does not have keeps it.
    placeholder = strings.REDACTED_SENSITIVE_VALUE
    stored = {"settings": {"token": placeholder, "password": placeholder}, "accounts": [{"token": placeholder}]}
    source = {"settings": {"token": None}, "accounts": [{"token": None}]}

    restored = restore_sensitive_values(stored, source)

    assert restored == {"settings": {"token": None, "password": placeholder}, "accounts": [{"token": None}]}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sensitive_in_target, expected", [(True, strings.REDACTED_SENSITIVE_VALUE), (False, "new value")]
)
@patch("db.repositories.resources.ResourceRepository.validate_patch")
@patch("db.repositories.resources.ResourceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
async def test_patch_resource_masks_with_the_template_of_the_target_version(
    _, __, resource_repo, sensitive_in_target, expected
):
    client_secret = {"type": "string", "updateable": True}
    source = masking_template({"client_secret": {**client_secret, "sensitive": not sensitive_in_target}})
    target = masking_template({"client_secret": {**client_secret, "sensitive": sensitive_in_target}}, version="1.1.0")
    template_repo = AsyncMock()
    template_repo.get_template_by_name_and_version.return_value = target
    template_repo.enrich_template = MagicMock(side_effect=lambda template, is_update=False: template.model_dump())
    resource_repo.update_item_with_etag = AsyncMock()
    resource = sample_resource()
    resource.templateVersion = "1.0.0"
    resource_patch = ResourcePatch(templateVersion="1.1.0", properties={"client_secret": "new value"})

    returned, _ = await resource_repo.patch_resource(
        resource,
        resource_patch,
        source,
        "etag",
        template_repo,
        AsyncMock(),
        create_test_user(),
        strings.RESOURCE_ACTION_UPDATE,
    )

    stored = resource_repo.update_item_with_etag.await_args.args[0]
    assert stored.templateVersion == "1.1.0"
    assert stored.properties["client_secret"] == expected
    assert returned.properties["client_secret"] == "new value"


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository.validate_patch")
async def test_patch_resource_replaces_same_length_array_on_ordinary_update(
    validate_patch_mock, resource_repo, resource_history_repo, basic_resource_template
):
    resource_repo.update_item_with_etag = AsyncMock(return_value=None)
    resource_history_repo.create_resource_history_item = AsyncMock()
    resource = sample_resource()
    resource.properties["items"] = [{"name": "old", "optional": "retained-only-by-old-value"}]
    patch = ResourcePatch(properties={"items": [{"name": "new"}]})

    await resource_repo.patch_resource(
        resource,
        patch,
        basic_resource_template,
        "some-etag",
        None,
        resource_history_repo,
        create_test_user(),
        strings.RESOURCE_ACTION_UPDATE,
    )

    assert resource.properties["items"] == [{"name": "new"}]


@pytest.mark.asyncio
async def test_validate_patch_with_good_fields_passes(resource_repo):
    """
    Make sure that patch is valid when updateable fields are included
    """
    template_repo = MagicMock()
    template_repo.enrich_template = MagicMock(return_value=sample_resource_template())
    template = sample_resource_template()

    # check it's valid when updating a single updateable prop
    patch = ResourcePatch(isEnabled=True, properties={"vm_size": "large"})
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
    patch = ResourcePatch(isEnabled=True, properties={"vm_size": "large", "unexpected_field": "surprise!"})
    with pytest.raises(ValidationError, match="Property 'unexpected_field' is unexpected."):
        await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)

    # check it's invalid when sending a bad value (new install)
    patch = ResourcePatch(isEnabled=True, properties={"vm_size": "huge"})
    with pytest.raises(ValidationError):
        await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_INSTALL)

    # check it's invalid when sending a bad value (update)
    patch = ResourcePatch(isEnabled=True, properties={"vm_size": "huge"})
    with pytest.raises(ValidationError):
        await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)

    # check it's invalid when trying to update a non-updateable field
    patch = ResourcePatch(isEnabled=True, properties={"vm_size": "large", "os_image": "Windows 11"})
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
    old_template["version"] = "0.1.0"

    # New template adds a new property 'new_property' that is not updateable
    new_template = sample_resource_template_with_new_property(version="0.2.0")

    # Mock the template repository
    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(
        return_value=parse_obj_as(ResourceTemplate, new_template)
    )
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    # Patch includes the new property during upgrade - this should be ALLOWED
    patch = ResourcePatch(templateVersion="0.2.0", properties={"new_property": "value1"})
    current_properties = {"title": "Test Title", "os_image": "Windows 11", "vm_size": "small"}

    # This should NOT raise a ValidationError
    await resource_repo.validate_patch(
        patch,
        template_repo,
        parse_obj_as(ResourceTemplate, old_template),
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties,
    )


@pytest.mark.asyncio
async def test_validate_patch_rejects_undeclared_nested_property_during_upgrade(resource_repo):
    old_template = sample_resource_template()
    old_template["version"] = "0.1.0"
    new_template = sample_resource_template_with_new_property(version="0.2.0")
    new_template["properties"]["parent_object"] = {
        "type": "object",
        "properties": {"declared_field": {"type": "string", "updateable": False}},
    }

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(
        return_value=parse_obj_as(ResourceTemplate, new_template)
    )
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    patch = ResourcePatch(templateVersion="0.2.0", properties={"parent_object": {"undeclared_field": "value1"}})

    with pytest.raises(ValidationError, match="Property 'parent_object.undeclared_field' is unexpected."):
        await resource_repo.validate_patch(
            patch,
            template_repo,
            parse_obj_as(ResourceTemplate, old_template),
            strings.RESOURCE_ACTION_UPDATE,
            current_properties={"title": "Test Title", "os_image": "Windows 11", "vm_size": "small"},
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
    template_repo.get_template_by_name_and_version = AsyncMock(
        return_value=parse_obj_as(ResourceTemplate, new_template)
    )
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    # Try to update existing non-updateable property during upgrade - this should FAIL
    patch = ResourcePatch(templateVersion="0.2.0", properties={"os_image": "Windows Server 2025"})

    with pytest.raises(ValidationError):
        await resource_repo.validate_patch(
            patch, template_repo, parse_obj_as(ResourceTemplate, old_template), strings.RESOURCE_ACTION_UPDATE
        )


@pytest.mark.asyncio
async def test_validate_patch_allows_unchanged_null_property_during_upgrade(resource_repo):
    """
    Test that during a template upgrade, non-updateable properties with existing None/null value sent unchanged pass validation.
    """
    old_template = sample_resource_template()
    new_template = copy.deepcopy(old_template)
    new_template["version"] = "0.2.0"

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(
        return_value=parse_obj_as(ResourceTemplate, new_template)
    )
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    current_properties = {"os_image": None, "vm_size": "small"}

    patch = ResourcePatch(templateVersion="0.2.0", properties={"os_image": None})

    resource_repo._validate_resource_parameters = MagicMock()

    await resource_repo.validate_patch(
        patch,
        template_repo,
        parse_obj_as(ResourceTemplate, old_template),
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties,
    )


@pytest.mark.asyncio
async def test_validate_patch_evaluates_allof_condition_against_current_properties(resource_repo):
    """
    Test that during upgrade, allOf conditional branches depending on existing properties evaluate against merged state.
    """
    old_template = sample_resource_template()
    old_template["properties"]["auth_type"] = {"type": "string", "updateable": False}

    new_template = copy.deepcopy(old_template)
    new_template["version"] = "0.2.0"
    new_template["properties"]["oauth_client_id"] = {"type": "string"}
    new_template["allOf"] = [
        {
            "if": {"properties": {"auth_type": {"const": "OAuth"}}},
            "then": {"properties": {"oauth_client_id": {"type": "string"}}},
        }
    ]
    new_template["unevaluatedProperties"] = False

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(
        return_value=parse_obj_as(ResourceTemplate, new_template)
    )
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    current_properties = {"auth_type": "OAuth", "title": "Test Title", "os_image": "Windows 11", "vm_size": "small"}

    patch = ResourcePatch(templateVersion="0.2.0", properties={"oauth_client_id": "client_123"})

    await resource_repo.validate_patch(
        patch,
        template_repo,
        parse_obj_as(ResourceTemplate, old_template),
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties,
    )


@pytest.mark.asyncio
async def test_validate_patch_rejects_system_properties_modification_during_upgrade(resource_repo):
    """
    Test that during a template upgrade, system properties (e.g. tre_id) are not treated as new properties and cannot be modified.
    """
    old_template_dict = sample_resource_template()
    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict["version"] = "0.2.0"

    old_template = parse_obj_as(ResourceTemplate, old_template_dict)
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(return_value=new_template)
    template_repo.enrich_template = MagicMock(
        side_effect=lambda t, is_update=False: {**t.model_dump(), "system_properties": {"tre_id": {"type": "string"}}}
    )

    current_properties = {"tre_id": "old_tre_id", "title": "Test Title", "os_image": "Windows 11", "vm_size": "small"}

    patch = ResourcePatch(templateVersion="0.2.0", properties={"tre_id": "new_tre_id"})

    with pytest.raises(ValidationError):
        await resource_repo.validate_patch(
            patch, template_repo, old_template, strings.RESOURCE_ACTION_UPDATE, current_properties=current_properties
        )


@pytest.mark.asyncio
async def test_validate_patch_allows_enum_property_update_during_upgrade_when_existing_value_is_invalid(resource_repo):
    """
    Test that during a template upgrade, updating a non-updateable enum property is allowed when the resource's current value is no longer in the target template's enum list.
    """
    old_template = sample_resource_template()

    new_template = copy.deepcopy(old_template)
    new_template["version"] = "0.2.0"
    new_template["properties"]["os_image"]["enum"] = ["Windows 11 Enterprise", "Windows Server 2025"]

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(
        return_value=parse_obj_as(ResourceTemplate, new_template)
    )
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    current_properties = {"title": "Test Title", "os_image": "Windows 11", "vm_size": "small"}

    patch = ResourcePatch(templateVersion="0.2.0", properties={"os_image": "Windows 11 Enterprise"})

    await resource_repo.validate_patch(
        patch,
        template_repo,
        parse_obj_as(ResourceTemplate, old_template),
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties,
    )


@pytest.mark.asyncio
async def test_validate_patch_allows_retained_system_properties_with_unevaluated_properties_false(resource_repo):
    """
    Test that during upgrade, retained system properties in current_properties pass validation when unevaluatedProperties is False.
    """
    old_template_dict = sample_resource_template()
    old_template_dict["unevaluatedProperties"] = False

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict["version"] = "0.2.0"
    new_template_dict["unevaluatedProperties"] = False

    old_template = parse_obj_as(ResourceTemplate, old_template_dict)
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(return_value=new_template)
    template_repo.enrich_template = MagicMock(
        side_effect=lambda t, is_update=False: {
            **t.model_dump(exclude_none=True),
            "unevaluatedProperties": False,
            "system_properties": {"tre_id": {"type": "string"}},
        }
    )

    current_properties = {"tre_id": "tre-1234", "title": "Test Title", "os_image": "Windows 11", "vm_size": "small"}

    patch = ResourcePatch(templateVersion="0.2.0", properties={"vm_size": "large"})

    await resource_repo.validate_patch(
        patch, template_repo, old_template, strings.RESOURCE_ACTION_UPDATE, current_properties=current_properties
    )


@pytest.mark.asyncio
async def test_validate_patch_rejects_empty_object_for_non_updateable_property(resource_repo):
    """
    Test that sending an empty dict for a non-updateable object property is validated and rejected.
    """
    template_dict = sample_resource_template()
    template_dict["properties"]["parent_object"] = {
        "type": "object",
        "updateable": False,
        "properties": {"child_prop": {"type": "string"}},
    }
    template = parse_obj_as(ResourceTemplate, template_dict)

    template_repo = MagicMock()
    template_repo.enrich_template = MagicMock(return_value=template_dict)

    patch = ResourcePatch(isEnabled=True, properties={"parent_object": {}})

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
    template_repo.get_template_by_name_and_version = AsyncMock(
        return_value=parse_obj_as(ResourceTemplate, new_template)
    )
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    # Update existing updateable property during upgrade - this should work
    patch = ResourcePatch(templateVersion="0.2.0", properties={"vm_size": "large"})
    current_properties = {"title": "Test Title", "os_image": "Windows 11", "vm_size": "small"}

    # This should NOT raise a ValidationError
    await resource_repo.validate_patch(
        patch,
        template_repo,
        parse_obj_as(ResourceTemplate, old_template),
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties,
    )


@pytest.mark.asyncio
async def test_validate_patch_allows_mix_of_new_and_updateable_properties_during_upgrade(resource_repo):
    """
    Test that during upgrade, you can specify both new non-updateable properties and existing updateable properties
    """
    # Old template
    old_template = sample_resource_template()

    # New template adds new_property
    new_template = sample_resource_template_with_new_property(version="0.2.0")

    # Mock the template repository
    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(
        return_value=parse_obj_as(ResourceTemplate, new_template)
    )
    template_repo.enrich_template = MagicMock(side_effect=[old_template, new_template])

    # Patch with both new non-updateable property and existing updateable property
    patch = ResourcePatch(templateVersion="0.2.0", properties={"new_property": "value1", "vm_size": "large"})
    current_properties = {"title": "Test Title", "os_image": "Windows 11", "vm_size": "small"}

    # This should NOT raise a ValidationError
    await resource_repo.validate_patch(
        patch,
        template_repo,
        parse_obj_as(ResourceTemplate, old_template),
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties,
    )


@pytest.mark.asyncio
async def test_validate_patch_rejects_user_patch_for_non_updateable_install_pipeline_property(resource_repo):
    """
    Make sure that external user PATCH cannot modify a non-updateable property even if it is in an install pipeline.
    """

    template_dict = sample_resource_template()
    template_dict["properties"]["my_inherited_property"] = {"type": "string", "updateable": False}
    template_dict["pipeline"] = {
        "install": [
            {
                "stepId": "main",
                "properties": [
                    {
                        "name": "my_inherited_property",
                        "value": "{{ resource.parent.properties.my_inherited_property }}",
                        "type": "string",
                    }
                ],
            }
        ]
    }

    template_repo = MagicMock()
    template_repo.enrich_template = MagicMock(return_value=template_dict)
    template = parse_obj_as(ResourceTemplate, template_dict)

    patch = ResourcePatch(isEnabled=True, properties={"my_inherited_property": "new_val"})

    with pytest.raises(ValidationError, match="Property 'my_inherited_property' is not updateable."):
        await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)


@pytest.mark.asyncio
async def test_validate_patch_rejects_user_patch_for_non_updateable_upgrade_pipeline_property(resource_repo):
    """
    Make sure that external user PATCH cannot modify a non-updateable property even if it is in an upgrade pipeline.
    """

    template_dict = sample_resource_template()
    template_dict["properties"]["my_inherited_property"] = {"type": "string", "updateable": False}
    template_dict["pipeline"] = {
        "upgrade": [
            {
                "stepId": "main",
                "properties": [
                    {
                        "name": "my_inherited_property",
                        "value": "{{ resource.parent.properties.my_inherited_property }}",
                        "type": "string",
                    }
                ],
            }
        ]
    }

    template_repo = MagicMock()
    template_repo.enrich_template = MagicMock(return_value=template_dict)
    template = parse_obj_as(ResourceTemplate, template_dict)

    patch = ResourcePatch(isEnabled=True, properties={"my_inherited_property": "new_val"})

    with pytest.raises(ValidationError, match="Property 'my_inherited_property' is not updateable."):
        await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)


@pytest.mark.asyncio
async def test_validate_patch_enforces_newly_required_properties_during_upgrade(resource_repo):
    """
    Test that during an upgrade, newly required properties defined in the target template are enforced.
    """
    old_template_dict = sample_resource_template()
    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict["version"] = "0.2.0"
    new_template_dict["properties"]["new_req_prop"] = {"type": "string"}
    new_template_dict["required"].append("new_req_prop")

    old_template = parse_obj_as(ResourceTemplate, old_template_dict)
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(return_value=new_template)
    template_repo.enrich_template = MagicMock(side_effect=[old_template_dict, new_template_dict])

    current_properties = {"display_name": "Test Resource", "vm_size": "small"}

    # Omit new_req_prop from patch -> should raise ValidationError
    patch = ResourcePatch(templateVersion="0.2.0", properties={"vm_size": "large"})

    with pytest.raises(ValidationError):
        await resource_repo.validate_patch(
            patch, template_repo, old_template, strings.RESOURCE_ACTION_UPDATE, current_properties=current_properties
        )


@pytest.mark.asyncio
async def test_get_all_property_keys_from_template_includes_allOf_conditional_properties(resource_repo):
    """
    Test that _get_all_property_keys_from_template correctly collects properties defined
    in conditional allOf blocks (both then and else clauses).
    """
    template_dict = sample_resource_template()
    template_dict["allOf"] = [
        {
            "if": {"properties": {"vm_size": {"const": "small"}}},
            "then": {"properties": {"conditional_then_property": {"type": "string"}}},
            "else": {"properties": {"conditional_else_property": {"type": "string"}}},
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
        "properties": {"child_a": {"type": "string"}, "child_b": {"type": "string"}},
    }
    template_repo.enrich_template = MagicMock(return_value=template_dict)
    template = parse_obj_as(ResourceTemplate, template_dict)

    patch = ResourcePatch(properties={"parent_obj": {"child_b": "new_value"}})

    # Should pass without raising ValidationError for missing sibling field child_a
    await resource_repo.validate_patch(patch, template_repo, template, strings.RESOURCE_ACTION_UPDATE)


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceTemplateRepository.enrich_template")
async def test_validate_patch_rejects_non_updateable_allOf_property(enrich_template_mock, resource_repo):
    """
    Test that validate_patch rejects attempts to patch non-updateable conditional properties inside allOf
    """
    template_dict = sample_resource_template()
    template_dict["allOf"] = [
        {
            "if": {"properties": {"vm_size": {"const": "small"}}},
            "then": {"properties": {"secret_conditional_field": {"type": "string", "updateable": False}}},
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
@patch("db.repositories.resources.ResourceTemplateRepository.get_template_by_name_and_version")
@patch("db.repositories.resources.ResourceTemplateRepository.enrich_template")
async def test_validate_patch_allows_new_nested_property_under_existing_object_during_upgrade(
    enrich_template_mock, get_template_mock, resource_repo
):
    """
    Test that during an upgrade, adding a newly-introduced nested property inside an existing object
    passes validation even if the parent object is not marked updateable.
    """
    old_template_dict = sample_resource_template()
    old_template_dict["properties"]["parent_object"] = {
        "type": "object",
        "updateable": False,
        "properties": {"existing_child": {"type": "string", "updateable": False}},
    }
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict["version"] = "0.2.0"
    new_template_dict["properties"]["parent_object"]["properties"]["new_child"] = {
        "type": "string",
        "updateable": False,
    }
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    get_template_mock.return_value = new_template
    enrich_template_mock.side_effect = [old_template_dict, new_template_dict]

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = get_template_mock
    template_repo.enrich_template = enrich_template_mock

    current_properties = {
        "title": "Test Title",
        "os_image": "Windows 11",
        "vm_size": "small",
        "parent_object": {"existing_child": "old_val"},
    }

    # Patching new_child during upgrade should be allowed
    patch = ResourcePatch(templateVersion="0.2.0", properties={"parent_object": {"new_child": "new_val"}})
    await resource_repo.validate_patch(
        patch, template_repo, old_template, strings.RESOURCE_ACTION_UPDATE, current_properties=current_properties
    )


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceTemplateRepository.get_template_by_name_and_version")
async def test_validate_patch_rejects_modifying_existing_nested_non_updateable_property_during_upgrade(
    get_template_mock, resource_repo
):
    """
    Test that during an upgrade, attempting to modify an existing non-updateable nested property
    fails validation.
    """
    old_template_dict = sample_resource_template()
    old_template_dict["properties"]["parent_object"] = {
        "type": "object",
        "updateable": False,
        "properties": {"existing_child": {"type": "string", "updateable": False}},
    }
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict["version"] = "0.2.0"
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    get_template_mock.return_value = new_template
    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = get_template_mock
    template_repo.enrich_template = MagicMock(return_value=new_template_dict)

    current_properties = {
        "title": "Test Title",
        "os_image": "Windows 11",
        "vm_size": "small",
        "parent_object": {"existing_child": "old_val"},
    }

    # Attempting to change existing_child during upgrade should raise ValidationError
    patch = ResourcePatch(templateVersion="0.2.0", properties={"parent_object": {"existing_child": "modified_val"}})
    with pytest.raises(ValidationError):
        await resource_repo.validate_patch(
            patch, template_repo, old_template, strings.RESOURCE_ACTION_UPDATE, current_properties=current_properties
        )


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceTemplateRepository.get_template_by_name_and_version")
async def test_patch_resource_removes_nested_properties_on_upgrade(
    get_template_mock, resource_repo, resource_history_repo
):
    """
    Test that patch_resource removes nested properties that were deleted in the new template version.
    """
    resource_repo.update_item_with_etag = AsyncMock(return_value=None)
    resource_history_repo.create_resource_history_item = AsyncMock()

    old_template_dict = sample_resource_template()
    old_template_dict["properties"]["parent_object"] = {
        "type": "object",
        "properties": {"kept_child": {"type": "string"}, "removed_child": {"type": "string"}},
    }
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict["version"] = "0.2.0"
    del new_template_dict["properties"]["parent_object"]["properties"]["removed_child"]
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    resource_repo.validate_template_version_patch = AsyncMock(return_value=new_template)

    get_template_mock.return_value = new_template
    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = get_template_mock
    template_repo.enrich_template = MagicMock(return_value=new_template_dict)

    user = create_test_user()
    resource = sample_resource()
    resource.properties = {
        "title": "Test Title",
        "os_image": "Windows 11",
        "vm_size": "small",
        "parent_object": {"kept_child": "val1", "removed_child": "val2"},
    }

    patch = ResourcePatch(templateVersion="0.2.0", properties={})

    _, returned_template = await resource_repo.patch_resource(
        resource,
        patch,
        old_template,
        "some-etag",
        template_repo,
        resource_history_repo,
        user,
        strings.RESOURCE_ACTION_UPDATE,
    )

    assert "removed_child" not in resource.properties["parent_object"]
    assert resource.properties["parent_object"]["kept_child"] == "val1"
    assert returned_template == new_template


@pytest.mark.asyncio
async def test_patch_resource_allows_full_array_items_when_adding_property(resource_repo, resource_history_repo):
    """Full array items sent by an upgrade remain valid when only one item property is new."""
    resource_repo.update_item_with_etag = AsyncMock(return_value=None)
    resource_history_repo.create_resource_history_item = AsyncMock()

    old_template_dict = sample_resource_template()
    old_template_dict["properties"]["redirect_uris"] = {
        "type": "array",
        "items": {"type": "object", "properties": {"name": {"type": "string"}}},
    }
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict["version"] = "0.2.0"
    new_template_dict["properties"]["redirect_uris"]["items"]["properties"]["value"] = {
        "type": "string",
        "default": "https://example.test",
    }
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    resource_repo.validate_template_version_patch = AsyncMock(return_value=new_template)
    template_repo = MagicMock()

    def enrich_template(template, is_update=False):
        enriched = copy.deepcopy(new_template_dict if template.version == "0.2.0" else old_template_dict)
        if not enriched.get("allOf"):
            enriched.pop("allOf", None)
        return enriched

    template_repo.enrich_template.side_effect = enrich_template

    user = create_test_user()
    resource = sample_resource()
    resource.properties = {
        "title": "Test Title",
        "os_image": "Windows 11",
        "vm_size": "small",
        "redirect_uris": [{"name": "primary"}],
    }
    patch = ResourcePatch(
        templateVersion="0.2.0", properties={"redirect_uris": [{"name": "primary", "value": "https://example.test"}]}
    )

    updated_resource, returned_template = await resource_repo.patch_resource(
        resource,
        patch,
        old_template,
        "some-etag",
        template_repo,
        resource_history_repo,
        user,
        strings.RESOURCE_ACTION_UPDATE,
    )

    assert updated_resource.properties["redirect_uris"] == [{"name": "primary", "value": "https://example.test"}]
    assert returned_template == new_template


@pytest.mark.asyncio
async def test_patch_resource_preserves_omitted_array_item_fields_during_upgrade(resource_repo, resource_history_repo):
    resource_repo.update_item_with_etag = AsyncMock(return_value=None)
    resource_history_repo.create_resource_history_item = AsyncMock()

    old_template_dict = sample_resource_template()
    old_template_dict["properties"]["redirect_uris"] = {
        "type": "array",
        "items": {"type": "object", "properties": {"protected": {"type": "string"}}, "required": ["protected"]},
    }
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict["version"] = "0.2.0"
    new_template_dict["properties"]["redirect_uris"]["items"]["properties"]["new_field"] = {
        "type": "string",
        "updateable": True,
    }
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    resource_repo.validate_template_version_patch = AsyncMock(return_value=new_template)
    template_repo = MagicMock()
    template_repo.enrich_template.side_effect = lambda template, is_update=False: copy.deepcopy(
        new_template_dict if template.version == "0.2.0" else old_template_dict
    )

    resource = sample_resource()
    resource.properties = {
        "title": "Test Title",
        "os_image": "Windows 11",
        "vm_size": "small",
        "redirect_uris": [{"protected": "keep-me"}],
    }
    patch = ResourcePatch(
        templateVersion="0.2.0",
        properties={"redirect_uris": [{"new_field": "new-value"}]},
    )

    await resource_repo.patch_resource(
        resource,
        patch,
        old_template,
        "some-etag",
        template_repo,
        resource_history_repo,
        create_test_user(),
        strings.RESOURCE_ACTION_UPDATE,
    )

    assert resource.properties["redirect_uris"] == [{"protected": "keep-me", "new_field": "new-value"}]


@pytest.mark.asyncio
async def test_validate_patch_allows_newly_required_array_item_property_during_upgrade(resource_repo):
    old_template_dict = sample_resource_template()
    old_template_dict["properties"]["redirect_uris"] = {
        "type": "array",
        "items": {"type": "object", "properties": {"name": {"type": "string"}, "value": {"type": "string"}}},
    }
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict["version"] = "0.2.0"
    new_template_dict["properties"]["redirect_uris"]["items"]["required"] = ["value"]
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = AsyncMock(return_value=new_template)
    template_repo.enrich_template = MagicMock(side_effect=[old_template_dict, new_template_dict])

    patch = ResourcePatch(
        templateVersion="0.2.0", properties={"redirect_uris": [{"name": "primary", "value": "https://example.test"}]}
    )
    current_properties = {
        "title": "Test Title",
        "os_image": "Windows 11",
        "vm_size": "small",
        "redirect_uris": [{"name": "primary"}],
    }

    await resource_repo.validate_patch(
        patch, template_repo, old_template, strings.RESOURCE_ACTION_UPDATE, current_properties=current_properties
    )


@pytest.mark.asyncio
async def test_patch_resource_removes_deleted_array_item_property_from_all_items(resource_repo, resource_history_repo):
    resource_repo.update_item_with_etag = AsyncMock(return_value=None)
    resource_history_repo.create_resource_history_item = AsyncMock()

    old_template_dict = sample_resource_template()
    old_template_dict["properties"]["redirect_uris"] = {
        "type": "array",
        "items": {"type": "object", "properties": {"name": {"type": "string"}, "value": {"type": "string"}}},
    }
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict["version"] = "0.2.0"
    del new_template_dict["properties"]["redirect_uris"]["items"]["properties"]["value"]
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    resource_repo.validate_template_version_patch = AsyncMock(return_value=new_template)
    template_repo = MagicMock()

    def enrich_template(template, is_update=False):
        return copy.deepcopy(new_template_dict if template.version == "0.2.0" else old_template_dict)

    template_repo.enrich_template = MagicMock(side_effect=enrich_template)

    resource = sample_resource()
    resource.properties = {
        "title": "Test Title",
        "os_image": "Windows 11",
        "vm_size": "small",
        "redirect_uris": [
            {"name": "primary", "value": "https://primary.example"},
            {"name": "secondary", "value": "https://secondary.example"},
        ],
    }
    patch = ResourcePatch(templateVersion="0.2.0", properties={})

    await resource_repo.patch_resource(
        resource,
        patch,
        old_template,
        "some-etag",
        template_repo,
        resource_history_repo,
        create_test_user(),
        strings.RESOURCE_ACTION_UPDATE,
    )

    assert resource.properties["redirect_uris"] == [{"name": "primary"}, {"name": "secondary"}]


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceTemplateRepository.get_template_by_name_and_version")
@patch("db.repositories.resources.ResourceTemplateRepository.enrich_template")
async def test_validate_patch_passes_parent_service_name_for_user_resources(
    enrich_template_mock, get_template_mock, resource_repo
):
    """
    Test that during a template upgrade for a UserResource, parent_service_name is passed
    to get_template_by_name_and_version.
    """
    old_template_dict = sample_resource_template()
    old_template_dict["resourceType"] = ResourceType.UserResource
    old_template_dict["parentWorkspaceService"] = "parent-service-name"
    old_template = parse_obj_as(UserResourceTemplate, old_template_dict)

    new_template = copy.deepcopy(old_template)
    new_template.version = "0.2.0"
    get_template_mock.return_value = new_template
    enrich_template_mock.return_value = old_template_dict

    # Mock template repository
    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = get_template_mock
    template_repo.enrich_template = enrich_template_mock

    patch = ResourcePatch(templateVersion="0.2.0", properties={})
    current_properties = {"title": "Test Title", "os_image": "Windows 11", "vm_size": "small"}
    await resource_repo.validate_patch(
        patch, template_repo, old_template, strings.RESOURCE_ACTION_UPDATE, current_properties=current_properties
    )

    get_template_mock.assert_called_once_with(
        old_template.name, "0.2.0", ResourceType.UserResource, parent_service_name="parent-service-name"
    )


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceRepository.create")
@patch("db.repositories.resources.ResourceTemplateRepository.get_template_by_name_and_version")
@patch("db.repositories.resources.ResourceTemplateRepository.enrich_template")
async def test_patch_resource_passes_parent_service_name_for_user_resources(
    enrich_template_mock, get_template_mock, create_repo_mock, resource_repo, resource_history_repo
):
    """
    Test that patch_resource passes parent_service_name to get_template_by_name_and_version
    when upgrading a UserResource.
    """
    resource_repo.update_item_with_etag = AsyncMock(return_value=None)
    resource_history_repo.create_resource_history_item = AsyncMock()

    mock_parent_repo = AsyncMock()
    mock_parent_repo.get_resource_by_id.return_value = MagicMock(templateName="parent-service-name")
    create_repo_mock.return_value = mock_parent_repo

    old_template_dict = sample_resource_template()
    old_template_dict["resourceType"] = ResourceType.UserResource
    old_template_dict["parentWorkspaceService"] = "parent-service-name"
    old_template = parse_obj_as(UserResourceTemplate, old_template_dict)

    new_template = copy.deepcopy(old_template)
    new_template.version = "0.2.0"
    get_template_mock.return_value = new_template
    enrich_template_mock.return_value = old_template_dict

    # Mock template repository
    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = get_template_mock
    template_repo.enrich_template = enrich_template_mock

    user = create_test_user()
    resource_dict = sample_resource().model_dump()
    resource_dict["resourceType"] = ResourceType.UserResource
    resource_dict["parentWorkspaceServiceId"] = "parent-service-id"
    resource_dict["templateVersion"] = "0.1.0"
    resource_dict["properties"] = {"title": "Test Title", "os_image": "Windows 11", "vm_size": "small"}
    resource = parse_obj_as(UserResource, resource_dict)

    resource_patch = ResourcePatch(templateVersion="0.2.0", properties={})

    await resource_repo.patch_resource(
        resource,
        resource_patch,
        old_template,
        "some-etag",
        template_repo,
        resource_history_repo,
        user,
        strings.RESOURCE_ACTION_UPDATE,
    )

    get_template_mock.assert_called_once_with(
        resource.templateName, "0.2.0", ResourceType.UserResource, "parent-service-name"
    )


def test_deep_dict_update_preserves_nested_siblings(resource_repo):
    target = {
        "display_name": "My Resource",
        "parent_object": {"sibling_field": "existing_value", "target_field": "old_value"},
    }
    patch = {"parent_object": {"target_field": "new_value", "added_field": "added_value"}}
    resource_repo._deep_dict_update(target, patch)
    assert target == {
        "display_name": "My Resource",
        "parent_object": {"sibling_field": "existing_value", "target_field": "new_value", "added_field": "added_value"},
    }


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceTemplateRepository.get_template_by_name_and_version")
@patch("db.repositories.resources.ResourceTemplateRepository.enrich_template")
async def test_validate_patch_allows_absent_target_required_non_updateable_property_on_upgrade(
    enrich_template_mock, get_template_mock, resource_repo
):
    """
    Test that an optional non-updateable property from the old template that becomes required in
    the target version can be initially populated on upgrade if absent from current properties.
    """
    old_template_dict = sample_resource_template()
    old_template_dict["properties"]["newly_required"] = {
        "type": "string",
        "title": "Newly Required Non-Updateable",
        "updateable": False,
    }
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    target_template_dict = copy.deepcopy(old_template_dict)
    target_template_dict["version"] = "0.2.0"
    target_template_dict["required"].append("newly_required")
    target_template = parse_obj_as(ResourceTemplate, target_template_dict)

    get_template_mock.return_value = target_template
    enrich_template_mock.return_value = target_template_dict

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = get_template_mock
    template_repo.enrich_template = enrich_template_mock

    # Resource current properties omit 'newly_required'
    current_properties = {"title": "Test Title", "os_image": "Windows 11", "vm_size": "small"}

    # Patch supplies 'newly_required' during upgrade
    patch = ResourcePatch(templateVersion="0.2.0", properties={"newly_required": "initial_value"})

    # Validation should succeed without throwing ValidationError
    await resource_repo.validate_patch(
        patch,
        template_repo,
        old_template,
        strings.RESOURCE_ACTION_UPDATE,
        current_properties=current_properties,
        target_template=target_template,
    )


@pytest.mark.asyncio
@patch("db.repositories.resources.ResourceTemplateRepository.get_template_by_name_and_version")
async def test_patch_resource_preserves_runtime_properties_on_upgrade(
    get_template_mock, resource_repo, resource_history_repo
):
    """
    Test that patch_resource preserves API-injected/runtime properties (e.g. workspace_subscription_id)
    that are absent from both current and target template schemas.
    """
    resource_repo.update_item_with_etag = AsyncMock(return_value=None)
    resource_history_repo.create_resource_history_item = AsyncMock()

    old_template_dict = sample_resource_template()
    old_template = parse_obj_as(ResourceTemplate, old_template_dict)

    new_template_dict = copy.deepcopy(old_template_dict)
    new_template_dict["version"] = "0.2.0"
    new_template = parse_obj_as(ResourceTemplate, new_template_dict)

    resource_repo.validate_template_version_patch = AsyncMock(return_value=new_template)
    get_template_mock.return_value = new_template

    template_repo = MagicMock()
    template_repo.get_template_by_name_and_version = get_template_mock
    template_repo.enrich_template = MagicMock(return_value=new_template_dict)

    user = create_test_user()
    resource = sample_resource()
    resource.properties = {
        "title": "Test Title",
        "os_image": "Windows 11",
        "vm_size": "small",
        "workspace_subscription_id": "sub-123-abc",  # Runtime property not in template schema
    }

    patch = ResourcePatch(templateVersion="0.2.0", properties={})

    updated_resource, _ = await resource_repo.patch_resource(
        resource,
        patch,
        old_template,
        "some-etag",
        template_repo,
        resource_history_repo,
        user,
        strings.RESOURCE_ACTION_UPDATE,
    )

    assert updated_resource.properties.get("workspace_subscription_id") == "sub-123-abc"
