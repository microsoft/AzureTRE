import pytest
from mock import patch

from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

from db.errors import EntityDoesNotExist, UnableToAccessDatabase
from models.schemas.workspace_template import get_sample_workspace_template_object
from resources import strings


pytestmark = pytest.mark.asyncio


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


# [GET] /workspace-templates/{template_name}
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
