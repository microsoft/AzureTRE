import pytest
from mock import patch

from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

from db.errors import EntityDoesNotExist
from resources import strings


pytestmark = pytest.mark.asyncio


# [GET] /workspaces
@patch("api.routes.workspaces.WorkspaceRepository.get_all_active_workspaces")
async def test_workspaces_get_empty_list_when_no_resources_exist(get_workspaces_mock, app: FastAPI, client: AsyncClient) -> None:
    get_workspaces_mock.return_value = []

    response = await client.get(app.url_path_for(strings.API_GET_ALL_WORKSPACES))
    assert response.json() == {"resources": []}


@patch("api.routes.workspaces.WorkspaceRepository.get_all_active_workspaces")
async def test_workspaces_get_list_returns_correct_data_when_resources_exist(get_workspaces_mock, app: FastAPI, client: AsyncClient) -> None:
    resources = [
        {
            "id": "afa000d3-82da-4bfc-b6e9-9a7853ef753e",
            "resourceSpec": {
                "name": "tre-workspace-vanilla",
                "version": "0.1.0"
            },
            "parameters": {
                "location": "europe"
            },
            "resourceType": "workspace",
            "status": "not_deployed",
            "isDeleted": False
        },
        {
            "id": "e87e30a6-e11b-4cf1-b523-8d278f8f492d",
            "resourceSpec": {
                "name": "tre-workspace-vanilla",
                "version": "0.1.0"
            },
            "parameters": {
                "location": "europe"
            },
            "resourceType": "workspace",
            "status": "not_deployed",
            "isDeleted": False
        },
    ]
    get_workspaces_mock.return_value = resources

    response = await client.get(app.url_path_for(strings.API_GET_ALL_WORKSPACES))
    resources_from_response = response.json()["resources"]
    assert len(resources_from_response) == len(resources)
    assert all((resource in resources for resource in resources_from_response))


# [GET] /workspaces/{workspace_id}
@patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
async def test_workspaces_id_get_returns_404_if_resource_is_not_found(get_workspace_mock, app: FastAPI, client: AsyncClient):
    get_workspace_mock.side_effect = EntityDoesNotExist

    response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_BY_ID, workspace_id="000000d3-82da-4bfc-b6e9-9a7853ef753e"))
    assert response.status_code == status.HTTP_404_NOT_FOUND


# [GET] /workspaces/{workspace_id}
@patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
async def test_workspaces_id_get_returns_422_if_workspace_id_is_not_a_uuid(get_workspace_mock, app: FastAPI, client: AsyncClient):
    get_workspace_mock.side_effect = EntityDoesNotExist

    response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_BY_ID, workspace_id="not_valid"))
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
async def test_workspaces_id_get_returns_workspace_if_found(get_workspace_mock, app: FastAPI, client: AsyncClient):
    sample_workspace = {
        "id": "afa000d3-82da-4bfc-b6e9-9a7853ef753e",
        "resourceSpec": {
            "name": "tre-workspace-vanilla",
            "version": "0.1.0",
        },
        "parameters": {
            "location": "europe"
        },
        "resourceType": "workspace",
        "status": "not_deployed",
        "isDeleted": False
    }
    get_workspace_mock.return_value = sample_workspace

    response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_BY_ID, workspace_id="afa000d3-82da-4bfc-b6e9-9a7853ef753e"))
    actual_resource = response.json()["resource"]
    assert actual_resource["id"] == sample_workspace["id"]
