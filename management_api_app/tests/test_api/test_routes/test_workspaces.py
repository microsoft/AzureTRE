import pytest
from mock import patch

from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

from db.errors import EntityDoesNotExist
from models.domain.resource import Status
from models.domain.workspace import Workspace
from models.schemas.workspace import get_sample_workspace
from resources import strings


pytestmark = pytest.mark.asyncio


def create_sample_workspace_object(workspace_id):
    return Workspace(
        id=workspace_id,
        description="My workspace",
        resourceTemplateName="tre-workspace-vanilla",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        status=Status.NotDeployed,
    )


def create_sample_workspace_input_data():
    return {
        "displayName": "My workspace",
        "description": "workspace for team X",
        "workspaceType": "tre-workspace-vanilla",
        "parameters": {}
    }


# [GET] /workspaces
@patch("api.routes.workspaces.WorkspaceRepository.get_all_active_workspaces")
async def test_workspaces_get_empty_list_when_no_resources_exist(get_workspaces_mock, app: FastAPI, client: AsyncClient) -> None:
    get_workspaces_mock.return_value = []

    response = await client.get(app.url_path_for(strings.API_GET_ALL_WORKSPACES))
    assert response.json() == {"workspaces": []}


@patch("api.routes.workspaces.WorkspaceRepository.get_all_active_workspaces")
async def test_workspaces_get_list_returns_correct_data_when_resources_exist(get_workspaces_mock, app: FastAPI, client: AsyncClient) -> None:
    workspaces = [get_sample_workspace("2fdc9fba-726e-4db6-a1b8-9018a2165748"), get_sample_workspace("000000d3-82da-4bfc-b6e9-9a7853ef753e")]
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
    workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
    sample_workspace = get_sample_workspace(workspace_id=workspace_id)
    get_workspace_mock.return_value = sample_workspace

    response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_BY_ID, workspace_id=workspace_id))
    actual_resource = response.json()["workspace"]
    assert actual_resource["id"] == sample_workspace["id"]


@patch("service_bus.service_bus.ServiceBus.send_resource_request_message")
@patch("api.routes.workspaces.WorkspaceRepository.save_workspace")
@patch("api.routes.workspaces.WorkspaceRepository.create_workspace_item")
async def test_workspaces_post_creates_workspace(create_workspace_item_mock, save_workspace_mock, send_resource_request_message_mock, app: FastAPI, client: AsyncClient):
    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"

    create_workspace_item_mock.return_value = create_sample_workspace_object(workspace_id)
    input_data = create_sample_workspace_input_data()

    response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=input_data)

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["workspaceId"] == workspace_id


@patch("service_bus.service_bus.ServiceBus.send_resource_request_message")
@patch("api.routes.workspaces.WorkspaceRepository.save_workspace")
@patch("api.routes.workspaces.WorkspaceRepository.create_workspace_item")
async def test_workspaces_post_calls_db_and_service_bus(create_workspace_item_mock, save_workspace_mock, send_resource_request_message_mock, app: FastAPI, client: AsyncClient):
    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"

    create_workspace_item_mock.return_value = create_sample_workspace_object(workspace_id)
    input_data = create_sample_workspace_input_data()

    await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=input_data)

    save_workspace_mock.assert_called_once()
    send_resource_request_message_mock.assert_called_once()


@patch("service_bus.service_bus.ServiceBus.send_resource_request_message")
@patch("api.routes.workspaces.WorkspaceRepository.save_workspace")
@patch("api.routes.workspaces.WorkspaceRepository.create_workspace_item")
async def test_workspaces_post_returns_202_on_successful_create(create_workspace_item_mock, save_workspace_mock, send_resource_request_message_mock, app: FastAPI, client: AsyncClient):
    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
    create_workspace_item_mock.return_value = create_sample_workspace_object(workspace_id)
    input_data = create_sample_workspace_input_data()

    response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=input_data)

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["workspaceId"] == workspace_id


@patch("service_bus.service_bus.ServiceBus.send_resource_request_message")
@patch("api.routes.workspaces.WorkspaceRepository.save_workspace")
@patch("api.routes.workspaces.WorkspaceRepository.create_workspace_item")
async def test_workspaces_post_returns_503_if_service_bus_call_fails(create_workspace_item_mock, save_workspace_mock, send_resource_request_message_mock, app: FastAPI, client: AsyncClient):
    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
    create_workspace_item_mock.return_value = create_sample_workspace_object(workspace_id)
    input_data = create_sample_workspace_input_data()

    send_resource_request_message_mock.side_effect = Exception

    response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=input_data)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@patch("api.routes.workspaces.WorkspaceRepository._get_template_version")
async def test_workspaces_post_returns_400_if_template_does_not_exist(get_template_version_mock, app: FastAPI, client: AsyncClient):
    get_template_version_mock.side_effect = EntityDoesNotExist
    input_data = create_sample_workspace_input_data()

    response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=input_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
