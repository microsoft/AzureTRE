import uuid

from mock import patch, MagicMock
import pytest

import db.repositories.workspaces
from db.errors import EntityDoesNotExist
from models.domain.resource import Status, ResourceType
from models.domain.workspace import Workspace
from models.schemas.workspace import WorkspaceInCreate


@patch('azure.cosmos.CosmosClient')
def test_get_all_active_workspaces_calls_db_with_correct_query(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)
    workspace_repo.container.query_items = MagicMock()
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.isDeleted = false'

    workspace_repo.get_all_active_workspaces()

    workspace_repo.container.query_items.assert_called_once_with(query=expected_query, enable_cross_partition_query=True)


@patch('azure.cosmos.CosmosClient')
def test_get_workspace_by_id_calls_db_with_correct_query(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)
    workspace_id = uuid.uuid4()
    workspace_repo.container.query_items = MagicMock(return_value=[{"id": str(workspace_id)}])
    expected_query = f'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.isDeleted = false AND c.id="{str(workspace_id)}"'

    workspace_repo.get_workspace_by_workspace_id(workspace_id)

    workspace_repo.container.query_items.assert_called_once_with(query=expected_query, enable_cross_partition_query=True)


@patch('azure.cosmos.CosmosClient')
def test_get_workspace_by_id_throws_entity_does_not_exist_if_item_does_not_exist(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)
    workspace_id = uuid.uuid4()
    workspace_repo.container.query_items = MagicMock(return_value=[])

    with pytest.raises(EntityDoesNotExist):
        workspace_repo.get_workspace_by_workspace_id(workspace_id)


@patch('azure.cosmos.CosmosClient')
def test_create_workspace_item_creates_a_workspace_with_the_right_values(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)

    workspace_type = "vanilla-tre"
    display_name = "my workspace"
    description = "some description"
    workspace_to_create = WorkspaceInCreate(workspaceType=workspace_type, displayName=display_name, description=description)

    workspace = workspace_repo.create_workspace_item(workspace_to_create)

    assert workspace.displayName == display_name
    assert workspace.description == description
    assert workspace.resourceSpecName == workspace_type
    assert workspace.resourceType == ResourceType.Workspace
    assert workspace.status == Status.NotDeployed
    assert "location" in workspace.resourceSpecParameters
    assert "workspace_id" in workspace.resourceSpecParameters
    assert "tre_id" in workspace.resourceSpecParameters
    assert "address_space" in workspace.resourceSpecParameters


@patch('azure.cosmos.CosmosClient')
def test_save_workspace_saves_the_items_to_the_database(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)
    workspace_repo.container.create_item = MagicMock()
    workspace = Workspace(
        id="1234",
        resourceSpecName="vanilla-tre",
        resourceSpecVersion="0.1.0",
        resourceSpecParameters={},
        status=Status.NotDeployed,
    )

    workspace_repo.save_workspace(workspace)

    workspace_repo.container.create_item.assert_called_once_with(body=workspace)
