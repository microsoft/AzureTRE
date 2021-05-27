import pytest
from mock import patch

from fastapi import FastAPI
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


@patch("api.routes.workspaces.WorkspaceRepository.get_all_active_resources")
async def test_empty_list_when_no_resources_exist(get_resources_mock, app: FastAPI, client: AsyncClient) -> None:
    get_resources_mock.return_value = []

    response = await client.get(app.url_path_for("workspaces:get-active-workspaces"))
    assert response.json() == {"resources": []}


@patch("api.routes.workspaces.WorkspaceRepository.get_all_active_resources")
async def test_list_returns_correct_data_when_resources_exist(get_resources_mock, app: FastAPI, client: AsyncClient) -> None:
    resources = [
        {"id": "63396b88-7ce6-440b-932c-827ebbae6d51", "description": "some description", "resourceType": "workspace", "status": "not_deployed"},
        {"id": "63396b88-7ce6-440b-932c-827ebbae6d52", "description": "some description", "resourceType": "workspace", "status": "not_deployed"}
    ]
    get_resources_mock.return_value = resources

    response = await client.get(app.url_path_for("workspaces:get-active-workspaces"))
    resources_from_response = response.json()["resources"]
    assert len(resources_from_response) == len(resources)
    assert all((resource in resources for resource in resources_from_response))
