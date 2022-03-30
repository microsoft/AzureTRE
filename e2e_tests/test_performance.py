import asyncio
import pytest

import config
from helpers import disable_and_delete_resource, post_resource
from resources import strings

pytestmark = pytest.mark.asyncio

@pytest.mark.performance
@pytest.mark.timeout(3000)
async def test_parallel_resource_creations(admin_token, workspace_owner_token, verify) -> None:

    tasks = []

    for i in range(2):
        payload = {
            "templateName": "tre-workspace-base",
            "properties": {
                "display_name": f'Perf Test Workspace {i}',
                "description": "workspace for perf test",
                "address_space_size": "small",
                "app_id": f"{config.TEST_WORKSPACE_APP_ID}"
            }
        }

        task = asyncio.create_task(post_resource(payload, strings.API_WORKSPACES, 'workspace', workspace_owner_token, admin_token, verify))
        tasks.append(task)

    resource_paths = await asyncio.gather(*tasks)

    # Now disable + delete them all in parallel
    tasks = []
    for ws, _ in resource_paths:
        task = asyncio.create_task(disable_and_delete_resource(f'/api{ws}', 'workspace', workspace_owner_token, admin_token, verify))
        tasks.append(task)

    await asyncio.gather(*tasks)


# @pytest.mark.performance
@pytest.mark.timeout(3000)
async def test_bulk_updates_to_ensure_each_resource_updated_in_series(admin_token, workspace_owner_token, verify) -> None:

    # create the workspace to use
    payload = {
        "templateName": "tre-workspace-base",
        "properties": {
            "display_name": "E2E test guacamole service",
            "address_space_size": "small",
            "app_id": f"{config.TEST_WORKSPACE_APP_ID}"
        }
    }

    workspace_path, workspace_id = await post_resource(payload, strings.API_WORKSPACES, 'workspace', workspace_owner_token, admin_token, verify)

    # create a guac service
    service_payload = {
        "templateName": "tre-service-guacamole",
        "properties": {
            "display_name": "Workspace service test",
            "openid_client_id": f"{config.TEST_WORKSPACE_APP_ID}"
        }
    }

    workspace_service_path, workspace_service_id = await post_resource(service_payload, f'/api{workspace_path}/{strings.API_WORKSPACE_SERVICES}', 'workspace_service', workspace_owner_token, None, verify)

    user_resource_payload = {
        "templateName": "tre-service-guacamole-windowsvm",
        "properties": {
            "display_name": "Perf test VM",
            "os_image": "Windows 10"
        }
    }

    # create the VMs in parallel, and wait for them to be created
    tasks = []
    for i in range(2):
        task = asyncio.create_task(post_resource(user_resource_payload, f'/api{workspace_service_path}/{strings.API_USER_RESOURCES}', 'user_resource', workspace_owner_token, None, verify))
        tasks.append(task)

    resource_paths = await asyncio.gather(*tasks)

    # Now patch them multiple times each, without waiting for the patch to complete, so the messages stack up - even if the RP has spare processed
    # Then patch each one a final time, with the wait. Once these are done we know all the patches are done
    tasks = []
    for resource_path, _ in resource_paths:
        for i in range(5):
            patch_payload = {
                "properties": {
                    "display_name": f'Perf test VM update {i}',
                }
            }
            post_resource(patch_payload, f'/api{resource_path}', 'user_resource', workspace_owner_token, None, verify, method="PATCH", wait=False)

        task = asyncio.create_task(post_resource(patch_payload, f'/api{resource_path}', 'user_resource', workspace_owner_token, None, verify, method="PATCH"))
        tasks.append(task)

    await asyncio.gather(*tasks)

    # clear up all the VMs in parallel
    tasks = []
    for resource_path, _ in resource_paths:
        task = asyncio.create_task(disable_and_delete_resource(f'/api{resource_path}', 'user_resource', workspace_owner_token, None, verify))
        tasks.append(task)

    await asyncio.gather(*tasks)

    # clear up workspace + service
    await disable_and_delete_resource(f'/api{workspace_service_path}', 'workspace_service', workspace_owner_token, None, verify)
    await disable_and_delete_resource(f'/api{workspace_path}', 'workspace', workspace_owner_token, admin_token, verify)
