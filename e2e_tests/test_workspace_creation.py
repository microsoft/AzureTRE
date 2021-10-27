import pytest

from httpx import AsyncClient
from starlette import status

import config
from helpers import get_auth_header, post_workspace_template, get_template
from resources import strings


pytestmark = pytest.mark.asyncio


workspace_templates = [
    (strings.BASE_WORKSPACE),
    (strings.INNEREYE)
]


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_templates)
async def test_get_workspace_templates(template_name, admin_token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_TEMPLATES}", headers=get_auth_header(admin_token))

        template_names = [templates["name"] for templates in response.json()["templates"]]
        assert (template_name in template_names), f"No {template_name} template found"


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_templates)
async def test_getting_templates(template_name, admin_token, verify) -> None:
    async with get_template(template_name, admin_token, verify) as response:
        assert (response.status_code == status.HTTP_200_OK), f"GET Request for {template_name} creation failed"


@pytest.mark.extended
@pytest.mark.timeout(1800)
async def test_create_devtestlabs_workspace(workspace_owner_token, admin_token, verify) -> None:
    payload = {
        "templateName": "tre-workspace-azureml-devtestlabs",
        "properties": {
            "display_name": "E2E test",
            "description": "workspace for E2E",
            "app_id": f"{config.AUTH_APP_CLIENT_ID}",
            "acr_name": f"{config.ACR_NAME}"
        }
    }
    await post_workspace_template(payload, workspace_owner_token, admin_token, verify)


@pytest.mark.extended
@pytest.mark.timeout(2400)
async def test_create_innereye_dl_workspace(workspace_owner_token, admin_token, verify) -> None:
    payload = {
        "templateName": "tre-workspace-azureml-devtestlabs",
        "properties": {
            "display_name": "E2E test",
            "description": "workspace for E2E",
            "app_id": f"{config.AUTH_APP_CLIENT_ID}",
            "acr_name": f"{config.ACR_NAME}"
        }
    }
    await post_workspace_template(payload, workspace_owner_token, admin_token, verify)


@pytest.mark.extended
@pytest.mark.timeout(3000)
async def test_create_innereye_dl_inference_workspace(workspace_owner_token, admin_token, verify) -> None:
    payload = {
        "templateName": "tre-workspace-azureml-devtestlabs",
        "properties": {
            "display_name": "E2E test",
            "description": "workspace for E2E",
            "app_id": f"{config.AUTH_APP_CLIENT_ID}",
            "acr_name": f"{config.ACR_NAME}"
        }
    }
    await post_workspace_template(payload, workspace_owner_token, admin_token, verify)
