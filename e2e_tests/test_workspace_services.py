import pytest

import config
from helpers import ping_guacamole_workspace_service
from resources.workspace import get_workspace_auth_details
from resources.resource import disable_and_delete_resource, post_resource
from resources import strings


pytestmark = pytest.mark.asyncio


@pytest.mark.extended
@pytest.mark.timeout(3300)
async def test_create_guacamole_service_into_base_workspace(admin_token, verify) -> None:

    payload = {
        "templateName": strings.BASE_WORKSPACE,
        "properties": {
            "display_name": "E2E test guacamole service",
            "description": "workspace for E2E",
            "address_space_size": "small",
            "client_id": f"{config.TEST_WORKSPACE_APP_ID}",
            "client_secret": f"{config.TEST_WORKSPACE_APP_SECRET}",
        }
    }
    if config.TEST_WORKSPACE_APP_PLAN != "":
        payload["properties"]["app_service_plan_sku"] = config.TEST_WORKSPACE_APP_PLAN

    workspace_path, workspace_id = await post_resource(payload, strings.API_WORKSPACES, access_token=admin_token, verify=verify)
    workspace_owner_token, scope_uri = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)

    service_payload = {
        "templateName": strings.GUACAMOLE_SERVICE,
        "properties": {
            "display_name": "Workspace service test",
            "description": "Workspace service for E2E test"
        }
    }

    workspace_service_path, workspace_service_id = await post_resource(service_payload, f'/api{workspace_path}/{strings.API_WORKSPACE_SERVICES}', workspace_owner_token, verify)

    await ping_guacamole_workspace_service(workspace_id, workspace_service_id, verify)

    # patch the guac service. we'll just update the display_name but this will still force a full deployment run
    # and essentially terraform no-op
    patch_payload = {
        "properties": {
            "display_name": "Updated Guac Name",
        }
    }

    await post_resource(patch_payload, f'/api{workspace_service_path}', workspace_owner_token, verify, method="PATCH")

    user_resource_payload = {
        "templateName": strings.GUACAMOLE_WINDOWS_USER_RESOURCE,
        "properties": {
            "display_name": "My VM",
            "description": "Will be using this VM for my research",
            "os_image": "Windows 10"
        }
    }

    user_resource_path, user_resource_id = await post_resource(user_resource_payload, f'/api{workspace_service_path}/{strings.API_USER_RESOURCES}', workspace_owner_token, verify, method="POST")

    await disable_and_delete_resource(f'/api{user_resource_path}', workspace_owner_token, verify)

    await disable_and_delete_resource(f'/api{workspace_service_path}', workspace_owner_token, verify)

    await disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify)


@pytest.mark.extended_aad
@pytest.mark.timeout(3300)
async def test_create_guacamole_service_into_aad_workspace(admin_token, verify) -> None:
    """This test will create a Guacamole service but will create a workspace and automatically register the AAD Application"""

    payload = {
        "templateName": strings.BASE_WORKSPACE,
        "properties": {
            "display_name": "E2E test guacamole service",
            "description": "workspace for E2E AAD",
            "address_space_size": "small",
            "client_id": "auto_create"
        }
    }
    if config.TEST_WORKSPACE_APP_PLAN != "":
        payload["properties"]["app_service_plan_sku"] = config.TEST_WORKSPACE_APP_PLAN

    workspace_path, workspace_id = await post_resource(payload, strings.API_WORKSPACES, access_token=admin_token, verify=verify)
    workspace_owner_token, scope_uri = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)

    service_payload = {
        "templateName": strings.GUACAMOLE_SERVICE,
        "properties": {
            "display_name": "Workspace service test",
            "description": "Workspace service for E2E test"
        }
    }

    workspace_service_path, workspace_service_id = await post_resource(service_payload, f'/api{workspace_path}/{strings.API_WORKSPACE_SERVICES}', workspace_owner_token, verify)

    await ping_guacamole_workspace_service(workspace_id, workspace_service_id, verify)

    # patch the guac service. we'll just update the display_name but this will still force a full deployment run
    # and essentially terraform no-op
    patch_payload = {
        "properties": {
            "display_name": "Updated Guac Name",
        }
    }

    await post_resource(patch_payload, f'/api{workspace_service_path}', workspace_owner_token, verify, method="PATCH")

    user_resource_payload = {
        "templateName": strings.GUACAMOLE_LINUX_USER_RESOURCE,
        "properties": {
            "display_name": "Linux VM",
            "description": "Extended Tests for Linux",
            "os_image": "Ubuntu 18.04"
        }
    }

    user_resource_path, user_resource_id = await post_resource(user_resource_payload, f'/api{workspace_service_path}/{strings.API_USER_RESOURCES}', workspace_owner_token, verify, method="POST")

    await disable_and_delete_resource(f'/api{user_resource_path}', workspace_owner_token, verify)

    await disable_and_delete_resource(f'/api{workspace_service_path}', workspace_owner_token, verify)

    await disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify)
