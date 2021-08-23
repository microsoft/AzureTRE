import pytest
from mock import patch, MagicMock

from jsonschema.exceptions import ValidationError

from db.errors import EntityDoesNotExist
from db.repositories.resources import ResourceRepository
from models.domain.resource import Deployment, Status
from models.domain.workspace import Workspace, ResourceType
from models.domain.resource_template import ResourceTemplate
from models.schemas.workspace import WorkspaceInCreate


@pytest.fixture
def resource_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield ResourceRepository(cosmos_client_mock)


@pytest.fixture
def workspace_input():
    return WorkspaceInCreate(workspaceType="vanilla-tre", properties={"display_name": "test", "description": "test", "app_id": "123"})


def test_delete_workspace_marks_workspace_as_deleted(resource_repo):
    resource_repo.update_item = MagicMock(return_value=None)

    workspace = Workspace(
        id="1234",
        resourceTemplateName="vanilla-tre",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.NotDeployed, message=""),
    )
    resource_repo.mark_resource_as_deleting(workspace)
    workspace.deployment.status = Status.Deleting
    resource_repo.update_item.assert_called_once_with(workspace)


def test_restore_deletion_status(resource_repo):
    resource_repo.update_item = MagicMock(return_value=None)

    workspace = Workspace(
        id="1234",
        resourceTemplateName="vanilla-tre",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.Deleting, message=""),
    )
    resource_repo.restore_previous_deletion_state(workspace, Status.Deployed)
    resource_repo.update_item.assert_called_once_with(workspace)


@patch("db.repositories.resources.ResourceRepository._get_enriched_template")
def test_validate_input_against_template_raises_entity_does_not_exist_if_template_does_not_exist(enriched_template_mock, resource_repo, workspace_input):
    enriched_template_mock.side_effect = EntityDoesNotExist

    with pytest.raises(ValueError):
        resource_repo.validate_input_against_template(workspace_input, "template_name", ResourceType.Workspace)


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
    workspace_create = WorkspaceInCreate(workspaceType="template1")
    with pytest.raises(ValidationError):
        resource_repo.validate_input_against_template("template1", workspace_create, ResourceType.Workspace)
