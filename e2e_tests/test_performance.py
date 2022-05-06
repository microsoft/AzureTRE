import asyncio
import pytest

import config
from helpers import disable_and_delete_resource, post_resource
from resources import strings

pytestmark = pytest.mark.asyncio


@pytest.mark.performance
@pytest.mark.timeout(3000)
async def test_parallel_resource_creations(admin_token, workspace_owner_token, verify) -> None:
    """Creates N workspaces in parallel, and creates a workspace service in each, in parallel"""

    number_workspaces = 2

    tasks = []

    for i in range(number_workspaces):
        payload = {
            "templateName": "tre-workspace-base",
            "properties": {
                "display_name": f'Perf Test Workspace {i}',
                "description": "workspace for perf test",
                "address_space_size": "small",
                "client_id": f"{config.TEST_WORKSPACE_APP_ID}"
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


@pytest.mark.performance
@pytest.mark.timeout(3000)
async def test_bulk_updates_to_ensure_each_resource_updated_in_series(admin_token, workspace_owner_token, verify) -> None:
    """Optionally creates a workspace and workspace service,
    then creates N number of VMs in parallel, patches each, and deletes them"""

    number_vms = 5
    number_updates = 5

    # To avoid creating + deleting a workspace + service in this test, set the vars for existing ones in ./templates/core/.env
    # PERF_TEST_WORKSPACE_ID | PERF_TEST_WORKSPACE_SERVICE_ID
    if config.PERF_TEST_WORKSPACE_ID == "":
        # create the workspace to use
        payload = {
            "templateName": "tre-workspace-base",
            "properties": {
                "display_name": "E2E test guacamole service",
                "description": "",
                "address_space_size": "small",
                "client_id": f"{config.TEST_WORKSPACE_APP_ID}"
            }
        }

        workspace_path, _ = await post_resource(payload, strings.API_WORKSPACES, 'workspace', workspace_owner_token, admin_token, verify)
    else:
        workspace_path = f"/workspaces/{config.PERF_TEST_WORKSPACE_ID}"

    if config.PERF_TEST_WORKSPACE_SERVICE_ID == "":
        # create a guac service
        service_payload = {
            "templateName": "tre-service-guacamole",
            "properties": {
                "display_name": "Workspace service test",
                "description": "",
                "ws_client_id": f"{config.TEST_WORKSPACE_APP_ID}",
                "ws_client_secret": f"{config.TEST_WORKSPACE_APP_SECRET}"
            }
        }

        workspace_service_path, _ = await post_resource(service_payload, f'/api{workspace_path}/{strings.API_WORKSPACE_SERVICES}', 'workspace_service', workspace_owner_token, None, verify)
    else:
        workspace_service_path = f"{workspace_path}/{strings.API_WORKSPACE_SERVICES}/{config.PERF_TEST_WORKSPACE_SERVICE_ID}"

    # Create the VMs in parallel, and wait for them to be created
    user_resource_payload = {
        "templateName": "tre-service-dev-vm",
        "properties": {
            "display_name": "Perf test VM",
            "description": "",
            "os_image": "Ubuntu 18.04"
        }
    }

    tasks = []
    for i in range(number_vms):
        task = asyncio.create_task(post_resource(user_resource_payload, f'/api{workspace_service_path}/{strings.API_USER_RESOURCES}', 'user_resource', workspace_owner_token, None, verify))
        tasks.append(task)

    resource_paths = await asyncio.gather(*tasks)

    # Now patch each VM multiple times each, without waiting for the patch to complete, so the messages stack up - even if the RP has spare processors.
    # Then disable / delete each one, with the wait. This performs a PATCH then DELETE. If these execute successfully we'll have a high level of confidence
    # that other operations were not in progress for that VM at that point (ie. the messages were processed in serial).
    tasks = []
    for resource_path, _ in resource_paths:
        for i in range(number_updates):
            patch_payload = {
                "properties": {
                    "display_name": f'Perf test VM update {i}',
                }
            }
            await post_resource(patch_payload, f'/api{resource_path}', 'user_resource', workspace_owner_token, None, verify, method="PATCH", wait=False)

        # clear up all the VMs in parallel
        # NOTE: Due to bug https://github.com/microsoft/AzureTRE/issues/1163 - this VM delete step currently fails
        task = asyncio.create_task(disable_and_delete_resource(f'/api{resource_path}', 'user_resource', workspace_owner_token, None, verify))
        tasks.append(task)

    await asyncio.gather(*tasks)

    # clear up workspace + service (if we created them)
    if config.PERF_TEST_WORKSPACE_SERVICE_ID == "":
        await disable_and_delete_resource(f'/api{workspace_service_path}', 'workspace_service', workspace_owner_token, None, verify)
    if config.PERF_TEST_WORKSPACE_ID == "":
        await disable_and_delete_resource(f'/api{workspace_path}', 'workspace', workspace_owner_token, admin_token, verify)
