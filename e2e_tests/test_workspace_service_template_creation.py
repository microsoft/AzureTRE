import pytest

from httpx import AsyncClient
from starlette import status

import config
from helpers import get_auth_header
from resources import strings


pytestmark = pytest.mark.asyncio


@pytest.mark.smoke
async def test_create_workspace_service_templates(token, verify) -> None:
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

        response = await client.post(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_SERVICE_TEMPLATES}", headers=get_auth_header(token), json=payload)

        assert (response.status_code == status.HTTP_201_CREATED or response.status_code == status.HTTP_409_CONFLICT), "The workspace service template creation service returned unexpected response."


@pytest.mark.smoke
async def test_get_workspace_service_templates(token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_SERVICE_TEMPLATES}", headers=get_auth_header(token))

        service_template_names = [service_templates["name"] for service_templates in response.json()["templates"]]
        assert (strings.TEST_WORKSPACE_SERVICE_TEMPLATE in service_template_names), f"No {strings.TEST_WORKSPACE_SERVICE_TEMPLATE} template found"
