import pytest

from httpx import AsyncClient
from starlette import status

import config
from helpers import get_auth_header, get_template
from resources import strings
from helpers import get_admin_token


pytestmark = pytest.mark.asyncio


workspace_templates = [
    (strings.BASE_WORKSPACE)
]

workspace_service_templates = [
    (strings.AZUREML_SERVICE),
    (strings.GUACAMOLE_SERVICE),
    (strings.INNEREYE_SERVICE),
    (strings.GITEA_SERVICE)
]

shared_service_templates = [
    (strings.FIREWALL_SHARED_SERVICE),
    (strings.GITEA_SHARED_SERVICE),
]


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_templates)
async def test_get_workspace_template(template_name, verify) -> None:
    admin_token = await get_admin_token(verify)
    # Test that the template is returned in GET request
    async with get_template(template_name, strings.API_WORKSPACE_TEMPLATES, admin_token, verify) as response:
        assert (response.status_code == status.HTTP_200_OK), f"GET Request for {template_name} creation failed"

    # Test thatt the template is returned in a list GET request
    async with AsyncClient(verify=verify) as client:
        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_TEMPLATES}", headers=get_auth_header(admin_token))

        template_names = [templates["name"] for templates in response.json()["templates"]]
        assert (template_name in template_names), f"No {template_name} template found"


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_service_templates)
async def test_get_workspace_service_templates(template_name, verify) -> None:
    # Test that the template is returned in GET request
    admin_token = await get_admin_token(verify)
    async with get_template(template_name, strings.API_WORKSPACE_SERVICE_TEMPLATES, admin_token, verify) as response:
        assert (response.status_code == status.HTTP_200_OK), f"GET Request for {template_name} failed"

    # Test that the template is returned in a list GET request
    async with AsyncClient(verify=verify) as client:
        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_SERVICE_TEMPLATES}", headers=get_auth_header(admin_token))

        template_names = [templates["name"] for templates in response.json()["templates"]]
        assert (template_name in template_names), f"No {template_name} template found"


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", shared_service_templates)
async def test_get_shared_service_templates(template_name, verify) -> None:
    # Test that the template is returned in GET request
    admin_token = await get_admin_token(verify)
    async with get_template(template_name, strings.API_SHARED_SERVICE_TEMPLATES, admin_token, verify) as response:
        assert (response.status_code == status.HTTP_200_OK), f"GET Request for {template_name} failed"

    # Test that the template is returned in a list GET request
    async with AsyncClient(verify=verify) as client:
        admin_token = await get_admin_token(verify)
        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_SHARED_SERVICE_TEMPLATES}", headers=get_auth_header(admin_token))

        template_names = [templates["name"] for templates in response.json()["templates"]]
        assert (template_name in template_names), f"No {template_name} template found"
