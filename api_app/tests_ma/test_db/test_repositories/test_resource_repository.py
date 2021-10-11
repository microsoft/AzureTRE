import pytest
from mock import patch, MagicMock

from jsonschema.exceptions import ValidationError

from db.errors import EntityDoesNotExist
from db.repositories.resources import ResourceRepository
from models.domain.resource import Deployment, Status
from models.domain.resource_template import ResourceTemplate
from models.domain.user_resource_template import UserResourceTemplate
from models.domain.workspace import Workspace, ResourceType
from models.schemas.workspace import WorkspaceInCreate


@pytest.fixture
def resource_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield ResourceRepository(cosmos_client_mock)


@pytest.fixture
def workspace_input():
    return WorkspaceInCreate(templateName="base-tre", properties={"display_name": "test", "description": "test", "app_id": "123"})


def test_delete_workspace_marks_workspace_as_deleted(resource_repo):
    resource_repo.update_item = MagicMock(return_value=None)

    workspace = Workspace(
        id="1234",
        resourceTemplateName="base-tre",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.NotDeployed, message=""),
    )
    resource_repo.mark_resource_as_deleting(workspace)
    workspace.deployment.status = Status.Deleting
    resource_repo.update_item.assert_called_once_with(workspace)


def test_restore_deletion_status_updates_db(resource_repo):
    resource_repo.update_item = MagicMock(return_value=None)

    workspace = Workspace(
        id="1234",
        resourceTemplateName="base-tre",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.Deleting, message=""),
    )
    resource_repo.restore_previous_deletion_state(workspace, Status.Deployed)
    resource_repo.update_item.assert_called_once_with(workspace)


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
                                                           properties={}).dict()

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
                                                           properties={}).dict()
    # missing display name
    workspace_input = WorkspaceInCreate(templateName="template1")

    with pytest.raises(ValidationError):
        resource_repo.validate_input_against_template("template1", workspace_input, ResourceType.Workspace)


@patch("db.repositories.resources.ResourceTemplateRepository.get_current_template")
def test_get_enriched_template_returns_the_enriched_template(get_current_mock, resource_repo):
    workspace_template = ResourceTemplate(id="abc", name="template1", description="", version="", resourceType=ResourceType.Workspace, current=True, required=[], properties={})
    get_current_mock.return_value = workspace_template

    template = resource_repo._get_enriched_template("template1", ResourceType.Workspace)

    get_current_mock.assert_called_once_with('template1', ResourceType.Workspace, '')
    assert "display_name" in template["properties"]


@patch("db.repositories.resources.ResourceTemplateRepository.get_current_template")
def test_get_enriched_template_returns_the_enriched_template_for_user_resources(get_current_mock, resource_repo):
    user_resource_template = UserResourceTemplate(id="abc", name="template1", description="", version="", resourceType=ResourceType.Workspace, current=True, required=[], properties={}, parentWorkspaceService="parent-template1")
    get_current_mock.return_value = user_resource_template

    template = resource_repo._get_enriched_template("template1", ResourceType.UserResource, "parent-template1")

    get_current_mock.assert_called_once_with('template1', ResourceType.UserResource, 'parent-template1')
    assert "display_name" in template["properties"]


def test_get_resource_dict_by_id_queries_db(resource_repo):
    item_id = "123"
    resource_repo.query = MagicMock(return_value=[{"id": item_id}])

    resource_repo.get_resource_dict_by_id(item_id)

    resource_repo.query.assert_called_once_with(query='SELECT * FROM c WHERE c.deployment.status != "deleted" AND c.id = "123"')


def test_get_resource_dict_by_id_raises_entity_does_not_exist_if_no_resources_come_back(resource_repo):
    item_id = "123"
    resource_repo.query = MagicMock(return_value=[])

    with pytest.raises(EntityDoesNotExist):
        resource_repo.get_resource_dict_by_id(item_id)
