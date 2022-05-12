import pytest

import config
from helpers import disable_and_delete_resource, get_workspace_owner_token, post_resource
from resources import strings


pytestmark = pytest.mark.asyncio


@pytest.mark.extended
@pytest.mark.timeout(3000)
async def test_create_guacamole_service_into_base_workspace(admin_token, verify) -> None:

    payload = {
        "templateName": "tre-workspace-base",
        "properties": {
            "display_name": "E2E test guacamole service",
            "description": "workspace for E2E",
            "address_space_size": "small",
            "client_id": f"{config.TEST_WORKSPACE_APP_ID}"
        }
    }

    workspace_path, workspace_id = await post_resource(payload, strings.API_WORKSPACES, access_token=admin_token, verify=verify)
    workspace_owner_token = await get_workspace_owner_token(admin_token=admin_token, workspace_id=workspace_id, verify=verify)

    service_payload = {
        "templateName": "tre-service-guacamole",
        "properties": {
            "display_name": "Workspace service test",
            "description": "Workspace service for E2E test",
            "ws_client_id": f"{config.TEST_WORKSPACE_APP_ID}",
            "ws_client_secret": f"{config.TEST_WORKSPACE_APP_SECRET}"
        }
    }

    workspace_service_path, workspace_service_id = await post_resource(service_payload, f'/api{workspace_path}/{strings.API_WORKSPACE_SERVICES}', workspace_owner_token, verify)

    # TODO: uncomment after fixing https://github.com/microsoft/AzureTRE/issues/1602
    # await ping_guacamole_workspace_service(workspace_id, workspace_service_id, workspace_owner_token, verify)

    # patch the guac service. we'll just update the display_name but this will still force a full deployment run
    # and essentially terraform no-op
    patch_payload = {
        "properties": {
            "display_name": "Updated Guac Name",
        }
    }

    await post_resource(patch_payload, f'/api{workspace_service_path}', workspace_owner_token, verify, method="PATCH")

    await disable_and_delete_resource(f'/api{workspace_service_path}', workspace_owner_token, verify)

    await disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify)


@pytest.mark.extended_aad
@pytest.mark.timeout(3000)
async def test_create_guacamole_service_into_aad_workspace(admin_token, workspace_owner_token, verify) -> None:
    """This test will create a Guacamole service but will create a workspace and automatically register the AAD Application"""

    payload = {
        "templateName": "tre-workspace-base",
        "properties": {
            "display_name": "E2E test guacamole service",
            "description": "workspace for E2E AAD",
            "address_space_size": "small",
            "client_id": "auto_create"
        }
    }

    workspace_path, workspace_id = await post_resource(payload, strings.API_WORKSPACES, access_token=admin_token, verify=verify)
    workspace_owner_token = await get_workspace_owner_token(admin_token=admin_token, workspace_id=workspace_id, verify=verify)

    service_payload = {
        "templateName": "tre-service-guacamole",
        "properties": {
            "display_name": "Workspace service test",
            "description": "Workspace service for E2E test",
            "ws_client_id": f"{config.TEST_WORKSPACE_APP_ID}",
            "ws_client_secret": f"{config.TEST_WORKSPACE_APP_SECRET}"
        }
    }

    workspace_service_path, workspace_service_id = await post_resource(service_payload, f'/api{workspace_path}/{strings.API_WORKSPACE_SERVICES}', workspace_owner_token, verify)

    # TODO: uncomment after fixing https://github.com/microsoft/AzureTRE/issues/1602
    # await ping_guacamole_workspace_service(workspace_id, workspace_service_id, workspace_owner_token, verify)

    # patch the guac service. we'll just update the display_name but this will still force a full deployment run
    # and essentially terraform no-op
    patch_payload = {
        "properties": {
            "display_name": "Updated Guac Name",
        }
    }

    await post_resource(patch_payload, f'/api{workspace_service_path}', workspace_owner_token, verify, method="PATCH")

    await disable_and_delete_resource(f'/api{workspace_service_path}', workspace_owner_token, verify)

    await disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify)
