import pytest
from mock import patch

from fastapi import FastAPI
from httpx import AsyncClient

from resources import strings


pytestmark = pytest.mark.asyncio


# [GET] /workspace-templates
@patch("api.routes.workspace_templates.WorkspaceTemplateRepository.get_workspace_template_names")
async def test_workspace_templates_returns_template_names(get_workspace_template_names_mock, app: FastAPI, client: AsyncClient):
    get_workspace_template_names_mock.return_value = ["template1", "template2"]

    response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_TEMPLATES))

    assert response.json()["templateNames"] == ["template1", "template2"]
