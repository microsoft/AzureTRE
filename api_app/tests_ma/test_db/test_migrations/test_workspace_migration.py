from unittest.mock import AsyncMock
import pytest
import pytest_asyncio
from mock import patch

from models.domain.resource import ResourceType
from db.migrations.workspaces import WorkspaceMigration

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def workspace_migrator():
    with patch('db.repositories.base.BaseRepository._get_container', return_value=AsyncMock()):
        with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
            workspace_migrator = await WorkspaceMigration.create(cosmos_client_mock)
            yield workspace_migrator


def get_sample_old_workspace(workspace_id: str = "7ab18f7e-ee8f-4202-8d46-747818ec76f4", spec_workspace_id: str = "0001") -> dict:
    return [{
        "id": workspace_id,
        "templateName": "tre-workspace-base",
        "templateVersion": "0.1.0",
        "properties": {
            "app_id": "03f18f7e-ee8f-4202-8d46-747818ec76f4",
            "azure_location": "westeurope",
            "workspace_id": spec_workspace_id,
            "tre_id": "mytre-dev-1234",
            "address_space_size": "small",
        },
        "resourceType": ResourceType.Workspace,
        "workspaceURL": "",
        "authInformation": {
            "sp_id": "f153f0f4-e89a-4456-b7ba-d0c46571d7c8",
            "roles": {
                "WorkspaceResearcher": "100358cf-5c65-4dfb-88b8-ed87fdc59db0",
                "WorkspaceOwner": "682df69e-bf3c-4606-85ab-75d70c0d510f"
            },
            "app_id": "03f18f7e-ee8f-4202-8d46-747818ec76f4"
        },
    }]


async def test_workspace_migration_moves_fields(workspace_migrator):
    workspace_migrator.query = AsyncMock(return_value=get_sample_old_workspace())

    assert (await workspace_migrator.moveAuthInformationToProperties())
