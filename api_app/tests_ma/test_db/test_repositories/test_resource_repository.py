import copy
import datetime
import uuid
import pytest
from mock import patch, MagicMock

from jsonschema.exceptions import ValidationError

from db.errors import EntityDoesNotExist
from db.repositories.resources import ResourceRepository
from models.domain.resource import Resource, ResourceHistoryItem
from models.domain.resource_template import ResourceTemplate
from models.domain.user_resource_template import UserResourceTemplate
from models.domain.workspace import ResourceType
from models.schemas.resource import ResourcePatch
from models.schemas.workspace import WorkspaceInCreate


FAKE_UPDATE_TIME = datetime.datetime(2022, 1, 1, 17, 5, 55)
FAKE_UPDATE_TIMESTAMP: float = FAKE_UPDATE_TIME.timestamp()
RESOURCE_ID = str(uuid.uuid4())


@pytest.fixture
def resource_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield ResourceRepository(cosmos_client_mock)


@pytest.fixture
def workspace_input():
    return WorkspaceInCreate(templateName="base-tre", properties={"display_name": "test", "description": "test", "app_id": "123"})


def sample_resource() -> Resource:
    return Resource(
        id=RESOURCE_ID,
        isActive=True,
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
        resourceVersion=0
    )


@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
@patch("db.repositories.resources.ResourceRepository._validate_resource_parameters", return_value=None)
def test_validate_input_against_template_returns_template_version_if_template_is_valid(_, enriched_template_mock, resource_repo, workspace_input):
    enriched_template_mock.return_value = ResourceTemplate(id="123",
                                                           name="template1",
                                                           description="description",
                                                           version="0.1.0",
                                                           resourceType=ResourceType.Workspace,
                                                           current=True,
                                                           required=[],
                                                           properties={},
                                                           actions=[]).dict()

    template_version = resource_repo.validate_input_against_template("template1", workspace_input, ResourceType.Workspace)

    assert template_version == "0.1.0"


@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
def test_validate_input_against_template_raises_value_error_if_template_does_not_exist(enriched_template_mock, resource_repo, workspace_input):
    enriched_template_mock.side_effect = EntityDoesNotExist

    with pytest.raises(ValueError):
        resource_repo.validate_input_against_template("template_name", workspace_input, ResourceType.Workspace)


@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
def test_validate_input_against_template_raises_value_error_if_the_user_resource_template_does_not_exist_for_the_given_workspace_service(enriched_template_mock, resource_repo, workspace_input):
    enriched_template_mock.side_effect = EntityDoesNotExist

    with pytest.raises(ValueError):
        resource_repo.validate_input_against_template("template_name", workspace_input, ResourceType.UserResource, "parent_template_name")


@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
def test_validate_input_against_template_raises_value_error_if_payload_is_invalid(enriched_template_mock, resource_repo):
    enriched_template_mock.return_value = ResourceTemplate(id="123",
                                                           name="template1",
                                                           description="description",
                                                           version="0.1.0",
                                                           resourceType=ResourceType.Workspace,
                                                           current=True,
                                                           required=["display_name"],
                                                           properties={},
                                                           actions=[]).dict()
    # missing display name
    workspace_input = WorkspaceInCreate(templateName="template1")

    with pytest.raises(ValidationError):
        resource_repo.validate_input_against_template("template1", workspace_input, ResourceType.Workspace)


@patch("db.repositories.resources.ResourceTemplateRepository.get_current_template")
def test_get_enriched_template_returns_the_enriched_template(get_current_mock, resource_repo):
    workspace_template = ResourceTemplate(id="abc", name="template1", description="", version="", resourceType=ResourceType.Workspace, current=True, required=[], properties={}, actions=[])
    get_current_mock.return_value = workspace_template

    template = resource_repo._get_enriched_template("template1", ResourceType.Workspace)

    get_current_mock.assert_called_once_with('template1', ResourceType.Workspace, '')
    assert "display_name" in template["properties"]


@patch("db.repositories.resources.ResourceTemplateRepository.get_current_template")
def test_get_enriched_template_returns_the_enriched_template_for_user_resources(get_current_mock, resource_repo):
    user_resource_template = UserResourceTemplate(id="abc", name="template1", description="", version="", resourceType=ResourceType.Workspace, current=True, required=[], properties={}, actions=[], parentWorkspaceService="parent-template1")
    get_current_mock.return_value = user_resource_template

    template = resource_repo._get_enriched_template("template1", ResourceType.UserResource, "parent-template1")

    get_current_mock.assert_called_once_with('template1', ResourceType.UserResource, 'parent-template1')
    assert "display_name" in template["properties"]


def test_get_resource_dict_by_id_queries_db(resource_repo):
    item_id = "123"
    resource_repo.query = MagicMock(return_value=[{"id": item_id}])

    resource_repo.get_resource_dict_by_id(item_id)

    resource_repo.query.assert_called_once_with(query='SELECT * FROM c WHERE c.isActive != false AND c.id = "123"')


def test_get_resource_dict_by_id_raises_entity_does_not_exist_if_no_resources_come_back(resource_repo):
    item_id = "123"
    resource_repo.query = MagicMock(return_value=[])

    with pytest.raises(EntityDoesNotExist):
        resource_repo.get_resource_dict_by_id(item_id)


@patch('db.repositories.resources.get_timestamp', return_value=FAKE_UPDATE_TIMESTAMP)
def test_patch_resource_preserves_property_history(_, resource_repo):
    """
    Tests that properties are copied into a history array and only certain values in the root are updated
    """

    resource_repo.update_item_with_etag = MagicMock(return_value=None)
    resource_patch = ResourcePatch(isEnabled=True, properties={'display_name': 'updated name'})

    etag = "some-etag-value"

    resource = sample_resource()
    expected_resource = sample_resource()
    expected_resource.history = [ResourceHistoryItem(isEnabled=True, resourceVersion=0, updatedWhen=FAKE_UPDATE_TIMESTAMP, properties={'display_name': 'initial display name', 'description': 'initial description', 'computed_prop': 'computed_val'})]
    expected_resource.properties['display_name'] = 'updated name'
    expected_resource.resourceVersion = 1

    resource_repo.patch_resource(resource, resource_patch, None, etag)
    resource_repo.update_item_with_etag.assert_called_once_with(expected_resource, etag)

    # now patch again
    new_resource = copy.deepcopy(expected_resource)  # new_resource is after the first patch
    new_patch = ResourcePatch(isEnabled=False, properties={'display_name': 'updated name 2'})
    expected_resource.history.append(
        ResourceHistoryItem(
            isEnabled=True,
            resourceVersion=1,
            updatedWhen=FAKE_UPDATE_TIMESTAMP,
            properties={'display_name': 'updated name', 'description': 'initial description', 'computed_prop': 'computed_val'}
        )
    )

    expected_resource.resourceVersion = 2
    expected_resource.properties['display_name'] = "updated name 2"
    expected_resource.isEnabled = False

    resource_repo.patch_resource(new_resource, new_patch, None, etag)
    resource_repo.update_item_with_etag.assert_called_with(expected_resource, etag)
