import pytest
from mock import patch

from fastapi import FastAPI
from starlette import status
from httpx import AsyncClient

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


@patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_current_workspace_template_by_name")
async def test_post_workspace_templates_does_not_create_a_template_with_bad_payload(_, app: FastAPI, client: AsyncClient):
    input_data = """
                    {
                        "blah": "blah"
                    }
    """

    response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_TEMPLATES), json=input_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
