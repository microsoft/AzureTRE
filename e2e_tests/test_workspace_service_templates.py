import pytest

from httpx import AsyncClient
from starlette import status

import config
from helpers import assert_status, get_auth_header, get_template
from resources import strings
from helpers import get_admin_token

pytestmark = pytest.mark.asyncio(loop_scope="session")

workspace_service_templates = [
    (strings.AZUREML_SERVICE),
    (strings.GUACAMOLE_SERVICE),
    (strings.GITEA_SERVICE)
]


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_service_templates)
async def test_get_workspace_service_templates(template_name, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        admin_token = await get_admin_token(verify)
        response = await client.get(f"{config.TRE_URL}{strings.API_WORKSPACE_SERVICE_TEMPLATES}", headers=get_auth_header(admin_token))

        template_names = [templates["name"] for templates in response.json()["templates"]]
        assert (template_name in template_names), f"No {template_name} template found"


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_service_templates)
async def test_get_workspace_service_template(template_name, verify) -> None:
    admin_token = await get_admin_token(verify)
    async with get_template(template_name, strings.API_WORKSPACE_SERVICE_TEMPLATES, admin_token, verify) as response:
        assert (response.status_code == status.HTTP_200_OK), f"GET Request for {template_name} failed"
        assert_status(response, [status.HTTP_200_OK], f"Failed to GET {template_name}")


@pytest.mark.smoke
async def test_create_workspace_service_templates(verify) -> None:
    async with AsyncClient(verify=verify) as client:
        payload = {
            "name": f"{strings.TEST_WORKSPACE_SERVICE_TEMPLATE}",
            "version": "0.0.1",
            "current": "true",
            "json_schema": {
                "$schema": "http://json-schema.org/draft-07/schema",
                "$id": "https://github.com/microsoft/AzureTRE/templates/workspaces/myworkspace/workspace_service.json",
                "type": "object",
                "title": "DONOTUSE",
                "description": "DO NOT USE",
                "required": [],
                "properties": {}
            }
        }

        admin_token = await get_admin_token(verify)
        response = await client.post(f"{config.TRE_URL}{strings.API_WORKSPACE_SERVICE_TEMPLATES}", headers=get_auth_header(admin_token), json=payload)

        assert_status(response, [status.HTTP_201_CREATED, status.HTTP_409_CONFLICT], "Failed to create workspace service template")
