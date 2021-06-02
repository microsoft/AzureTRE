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
    assert response.json() == {"workspaces": []}


@patch("api.routes.workspaces.WorkspaceRepository.get_all_active_workspaces")
async def test_workspaces_get_list_returns_correct_data_when_resources_exist(get_workspaces_mock, app: FastAPI, client: AsyncClient) -> None:
    workspaces = [
        {
            "id": "933ad738-7265-4b5f-9eae-a1a62928772e",
            "resourceSpec": {
                "name": "My workspace",
                "version": "0.1.0",
                "parameters": [
                    {"name": "location", "value": "westeurope"},
                    {"name": "workspace_id", "value": "0001"},
                    {"name": "core_id", "value": "mytre-dev-1234"},
                    {"name": "address_space", "value": "10.2.1.0/24"}
                ]
            },
            "resourceType": "workspace",
            "status": "not_deployed",
            "isDeleted": False,
            "friendlyName": "my friendly name",
            "description": "some description",
            "workspaceURL": ""
        },
        {
            "id": "2fdc9fba-726e-4db6-a1b8-9018a2165748",
            "resourceSpec": {
                "name": "My workspace",
                "version": "0.1.0",
                "parameters": [
                    {"name": "location", "value": "westeurope"},
                    {"name": "workspace_id", "value": "0002"},
                    {"name": "core_id", "value": "mytre-dev-3142"},
                    {"name": "address_space", "value": "10.2.1.0/24"}
                ]
            },
            "resourceType": "workspace",
            "status": "not_deployed",
            "isDeleted": False,
            "friendlyName": "my friendly name",
            "description": "some description",
            "workspaceURL": ""
        }
    ]
    get_workspaces_mock.return_value = workspaces

    response = await client.get(app.url_path_for(strings.API_GET_ALL_WORKSPACES))
    workspaces_from_response = response.json()["workspaces"]
    assert len(workspaces_from_response) == len(workspaces)
    assert all((workspace in workspaces for workspace in workspaces_from_response))


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
        "id": "933ad738-7265-4b5f-9eae-a1a62928772e",
        "resourceSpec": {
            "name": "My workspace",
            "version": "0.1.0",
            "parameters": [
                {"name": "location", "value": "westeurope"},
                {"name": "workspace_id", "value": "0001"},
                {"name": "core_id", "value": "mytre-dev-1234"},
                {"name": "address_space", "value": "10.2.1.0/24"}
            ]
        },
        "resourceType": "workspace",
        "status": "not_deployed",
        "isDeleted": False,
        "friendlyName": "hello",
        "description": "some description",
        "workspaceURL": ""
    }
    get_workspace_mock.return_value = sample_workspace

    response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_BY_ID, workspace_id="afa000d3-82da-4bfc-b6e9-9a7853ef753e"))
    actual_resource = response.json()["workspace"]
    assert actual_resource["id"] == sample_workspace["id"]
