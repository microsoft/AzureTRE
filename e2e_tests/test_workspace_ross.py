import pytest

import config
from helpers import disable_and_delete_resource, post_resource
from resources import strings


pytestmark = pytest.mark.asyncio


@pytest.mark.rossclean
@pytest.mark.timeout(3000)
async def test_ross_clean_workspace(admin_token, verify) -> None:

    # workspace_service_paths = ["/workspaces/9c208e42-1c4e-4670-83f5-f897a0b4f170/workspace-services/b52ff52e-e4f2-4393-8505-f08fb87ef190"]
    # for workspace_service_path in workspace_service_paths:
    #     await disable_and_delete_resource(f'/api{workspace_service_path}', 'workspace_service', workspace_owner_token, None, verify)

    workspace_paths = ["/workspaces/52826975-e571-4dd2-825c-8353f071da79"]
    for workspace_path in workspace_paths:
        await disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify)


@pytest.mark.ross
@pytest.mark.timeout(3000)
async def test_ross_create_base_workspace(admin_token, workspace_owner_token, verify) -> None:

    payload = {
        "templateName": "tre-workspace-base",
        "properties": {
            "display_name": "E2E test guacamole service",
            "description": "workspace for E2E",
            "address_space_size": "small",
            "client_id": f"{config.TEST_WORKSPACE_APP_ID}"
        }
    }

    workspace_path, _ = await post_resource(payload, strings.API_WORKSPACES, 'workspace', workspace_owner_token, admin_token, verify)

    service_payload = {
        "templateName": "tre-service-guacamole",
        "properties": {
            "display_name": "Workspace service test",
            "description": "Workspace service for E2E test",
            "ws_client_id": f"{config.TEST_WORKSPACE_APP_ID}",
            "ws_client_secret": f"{config.TEST_WORKSPACE_APP_SECRET}"
        }
    }

    workspace_service_path, workspace_service_id = await post_resource(service_payload, f'/api{workspace_path}/{strings.API_WORKSPACE_SERVICES}', 'workspace_service', workspace_owner_token, None, verify)
