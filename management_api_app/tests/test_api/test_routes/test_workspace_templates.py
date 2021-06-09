import json
import copy
import pytest
from mock import patch

from fastapi import FastAPI
from starlette import status
from httpx import AsyncClient

from db.errors import EntityDoesNotExist, UnableToAccessDatabase
from models.schemas.workspace_template import get_sample_workspace_template_object
from resources import strings


pytestmark = pytest.mark.asyncio
payload = {
    "name": "my-tre-workspace",
    "version": "0.0.1",
    "description": "workspace template for great product",
    "properties": [{"blah": "blah"}],
    "resourceType": "workspace",
    "current": True
}

# [GET] /workspace-templates


@patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_workspace_template_names")
async def test_workspace_templates_returns_template_names(get_workspace_template_names_mock, app: FastAPI, client: AsyncClient):
    expected_template_names = ["template1", "template2"]
    get_workspace_template_names_mock.return_value = expected_template_names

    response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_TEMPLATES))

    actual_template_names = response.json()["templateNames"]
    assert len(actual_template_names) == len(expected_template_names)
    for name in expected_template_names:
        assert name in actual_template_names


async def test_post_does_not_create_a_template_with_bad_payload(app: FastAPI, client: AsyncClient):
    input_data = """
                    {
                        "blah": "blah"
                    }
    """

    response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES), json=input_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@patch("api.routes.workspace_templates.WorkspaceTemplateRepository.create_workspace_template_item")
@patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_current_workspace_template_by_name")
async def test_when_updating_current_and_template_not_found_create_one(get_current_mock, create_item_mock, app: FastAPI, client: AsyncClient):
    get_current_mock.side_effect = EntityDoesNotExist

    response_content = copy.deepcopy(payload)
    response_content["id"] = "1234"
    create_item_mock.return_value = response_content

    response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES), json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    assert json.loads(response.text)["workspaceTemplate"] == response_content


@patch("api.routes.workspace_templates.WorkspaceTemplateRepository.update_item")
@patch("api.routes.workspace_templates.WorkspaceTemplateRepository.create_workspace_template_item")
@patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_current_workspace_template_by_name")
async def test_when_updating_current_and_template_found_update_and_add(get_current_mock, create_item_mock,
                                                                       update_item_mock,
                                                                       app: FastAPI, client: AsyncClient):
    get_current_mock.return_value = {"current": "true"}

    response_content = copy.deepcopy(payload)
    response_content["id"] = "1234"
    create_item_mock.return_value = response_content

    response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES), json=payload)

    expected_template = {"current": "false"}
    update_item_mock.assert_called_once_with(expected_template)
    assert response.status_code == status.HTTP_201_CREATED
    assert json.loads(response.text)["workspaceTemplate"] == response_content


@patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_workspace_template_by_name_and_version")
async def test_when_not_updating_current_and_same_template_exists_gives_409(mock, app: FastAPI, client: AsyncClient):
    payload["current"] = "false"
    mock.return_value = ["exists"]

    response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES), json=payload)

    assert response.status_code == status.HTTP_409_CONFLICT


@patch("api.routes.workspace_templates.WorkspaceTemplateRepository.create_workspace_template_item")
@patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_workspace_template_by_name_and_version")
async def test_when_not_updating_current_a_unique_template_is_saved(get_mock, create_mock, app: FastAPI, client: AsyncClient):
    payload["current"] = False
    get_mock.side_effect = EntityDoesNotExist

    response_content = copy.deepcopy(payload)
    response_content["id"] = "1234"
    create_mock.return_value = response_content

    response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES), json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    assert json.loads(response.text)["workspaceTemplate"] == response_content


@patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_current_workspace_template_by_name")
async def test_workspace_templates_by_name_returns_workspace_template(get_workspace_template_by_name_mock, app: FastAPI, client: AsyncClient):
    get_workspace_template_by_name_mock.return_value = get_sample_workspace_template_object(template_name="template1")

    response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_TEMPLATE_BY_NAME, template_name="tre-workspace-vanilla"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["workspaceTemplate"]["name"] == "template1"


@patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_current_workspace_template_by_name")
async def test_workspace_templates_by_name_returns_404_if_template_does_not_exist(get_workspace_template_by_name_mock, app: FastAPI, client: AsyncClient):
    get_workspace_template_by_name_mock.side_effect = EntityDoesNotExist

    response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_TEMPLATE_BY_NAME, template_name="tre-workspace-vanilla"))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_current_workspace_template_by_name")
async def test_workspace_templates_by_name_returns_503_on_database_error(get_workspace_template_by_name_mock, app: FastAPI, client: AsyncClient):
    get_workspace_template_by_name_mock.side_effect = UnableToAccessDatabase

    response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_TEMPLATE_BY_NAME, template_name="tre-workspace-vanilla"))

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
