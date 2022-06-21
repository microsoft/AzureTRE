import pytest

import config
from resources.workspace import get_workspace_auth_details
from resources.resource import disable_and_delete_resource, post_resource

from resources import strings


pytestmark = pytest.mark.asyncio


@pytest.mark.clean
@pytest.mark.timeout(3000)
async def test_clean(admin_token, verify) -> None:
    """This test will create a Guacamole service but will create a workspace and automatically register the AAD Application"""

    workspace_id = "a4e9a1bc-3046-4974-a537-fed1e0ce765b"

    workspace_path = f"/workspaces/{workspace_id}"
    workspace_service_path = f"{workspace_path}/workspace-services/aa7e9e9d-c159-4fd1-9fb5-110d8ac25b6e"
    user_resource_id = "ba4349a1-a9ea-48c2-b5c6-2d122bee7cd6"
    user_resource_path = f"{workspace_service_path}/{strings.API_USER_RESOURCES}/{user_resource_id}"

    workspace_owner_token, scope_uri = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)

    #await disable_and_delete_resource(f'/api{user_resource_path}', workspace_owner_token, verify)

    await disable_and_delete_resource(f'/api{workspace_service_path}', workspace_owner_token, verify)

    await disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify)


@pytest.mark.wip
@pytest.mark.timeout(3000)
async def test_ross(admin_token, verify) -> None:
    """This test will create a Guacamole service but will create a workspace and automatically register the AAD Application"""

    workspace_id = "59f4b7d3-8916-4a2b-9a5f-bf92029fd974"

    workspace_path = f"/workspaces/{workspace_id}"
    # workspace_service_path = f"{workspace_path}/workspace-services/d4da3f16-07f1-41ee-a6e5-90946ca845b3"
    # user_resource_id = "c49ae4d0-3a38-4250-899a-f6e1c2a4a8a6"

    #workspace_owner_token, scope_uri = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)

    # user_resource_payload = {
    #     "templateName": "tre-service-guacamole-linuxvm",
    #     "properties": {
    #         "display_name": "My VM",
    #         "description": "Will be using this VM for my research",
    #         "os_image": "Ubuntu 18.04"
    #     }
    # }

    #user_resource_path, user_resource_id = await post_resource(user_resource_payload, f'/api{workspace_service_path}/{strings.API_USER_RESOURCES}', workspace_owner_token, verify, method="POST")
    #user_resource_path = f"{workspace_service_path}/{strings.API_USER_RESOURCES}/{user_resource_id}"

    #await disable_and_delete_resource(f'/api{user_resource_path}', workspace_owner_token, verify)

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

    await disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify)
