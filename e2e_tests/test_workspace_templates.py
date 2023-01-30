import pytest

from httpx import AsyncClient
from starlette import status

import config
from helpers import assert_status, get_auth_header, get_template
from resources import strings
from helpers import get_admin_token


pytestmark = pytest.mark.asyncio


workspace_templates = [
    (strings.BASE_WORKSPACE)
]


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_templates)
async def test_get_workspace_templates(template_name, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        admin_token = await get_admin_token(verify)
        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_TEMPLATES}", headers=get_auth_header(admin_token))

        template_names = [templates["name"] for templates in response.json()["templates"]]
        assert (template_name in template_names), f"No {template_name} template found"


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_templates)
async def test_get_workspace_template(template_name, verify) -> None:
    admin_token = await get_admin_token(verify)
    async with get_template(template_name, strings.API_WORKSPACE_TEMPLATES, admin_token, verify) as response:
        assert_status(response, [status.HTTP_200_OK], f"Failed to GET template: {template_name}")
