import pytest
from httpx import AsyncClient
from starlette import status

import config
from helpers import disable_and_delete_resource, get_service_template, post_resource, get_auth_header, ping_guacamole_workspace_service
from resources import strings

pytestmark = pytest.mark.asyncio

workspace_service_templates = [
    (strings.AZUREML_SERVICE),
    (strings.DEVTESTLABS_SERVICE),
    (strings.GUACAMOLE_SERVICE),
    (strings.INNEREYE_SERVICE),
    (strings.GITEA_SERVICE)
]


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_service_templates)
async def test_get_workspace_service_templates(template_name, admin_token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_SERVICE_TEMPLATES}", headers=get_auth_header(admin_token))

        template_names = [templates["name"] for templates in response.json()["templates"]]
        assert (template_name in template_names), f"No {template_name} template found"


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_service_templates)
async def test_getting_templates(template_name, admin_token, verify) -> None:
    async with get_service_template(template_name, admin_token, verify) as response:
        assert (response.status_code == status.HTTP_200_OK), f"GET Request for {template_name} failed"


@pytest.mark.extended
@pytest.mark.timeout(3000)
async def test_create_guacamole_service_into_base_workspace(admin_token, workspace_owner_token, verify) -> None:

    payload = {
        "templateName": "tre-workspace-base",
        "properties": {
            "display_name": "E2E test guacamole service",
            "description": "workspace for E2E",
            "address_space_size": "small",
            "app_id": f"{config.TEST_WORKSPACE_APP_ID}"
        }
    }

    workspace_path, workspace_id = await post_resource(payload, strings.API_WORKSPACES, 'workspace', workspace_owner_token, admin_token, verify)

    service_payload = {
        "templateName": "tre-service-guacamole",
        "properties": {
            "display_name": "Workspace service test",
            "description": "Workspace service for E2E test",
            "openid_client_id": f"{config.TEST_WORKSPACE_APP_ID}"
        }
    }

    workspace_service_path, workspace_service_id = await post_resource(service_payload, f'/api{workspace_path}/{strings.API_WORKSPACE_SERVICES}', 'workspace_service', workspace_owner_token, None, verify)

    await ping_guacamole_workspace_service(workspace_id, workspace_service_id, workspace_owner_token, verify)

    # patch the guac service. we'll just update the display_name but this will still force a full deployment run
    # and essentially terraform no-op
    patch_payload = {
        "properties": {
            "display_name": "Updated Guac Name",
        }
    }

    await post_resource(patch_payload, f'/api{workspace_service_path}', 'workspace_service', workspace_owner_token, None, verify, method="PATCH")

    await disable_and_delete_resource(f'/api{workspace_service_path}', 'workspace_service', workspace_owner_token, None, verify)

    await disable_and_delete_resource(f'/api{workspace_path}', 'workspace', workspace_owner_token, admin_token, verify)
