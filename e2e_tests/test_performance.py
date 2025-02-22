import asyncio
import pytest
import config
from e2e_tests.conftest import disable_and_delete_tre_resource, disable_and_delete_ws_resource
from resources.workspace import get_workspace_auth_details
from resources.resource import post_resource
from resources import strings

from helpers import get_admin_token

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.performance
@pytest.mark.timeout(3000)
async def test_parallel_resource_creations(verify) -> None:
    """Creates N workspaces in parallel, and creates a workspace service in each, in parallel"""

    number_workspaces = 2

    tasks = []

    for i in range(number_workspaces):
        payload = {
            "templateName": strings.BASE_WORKSPACE,
            "properties": {
                "display_name": f'Perf Test Workspace {i}',
                "description": "workspace for perf test",
                "address_space_size": "small",
                "auth_type": "Manual",
                "client_id": f"{config.TEST_WORKSPACE_APP_ID}"
            }
        }

        admin_token = await get_admin_token(verify)
        task = asyncio.create_task(post_resource(payload=payload, endpoint=strings.API_WORKSPACES, access_token=admin_token, verify=verify))
        tasks.append(task)

    resource_paths = await asyncio.gather(*tasks)

    # Now disable + delete them all in parallel
    tasks = []
    for workspace_path, _ in resource_paths:
        task = asyncio.create_task(disable_and_delete_tre_resource(workspace_path, verify))
        tasks.append(task)

    await asyncio.gather(*tasks)


@pytest.mark.skip
@pytest.mark.performance
@pytest.mark.timeout(3000)
async def test_bulk_updates_to_ensure_each_resource_updated_in_series(verify) -> None:
    """Optionally creates a workspace and workspace service,
    then creates N number of VMs in parallel, patches each, and deletes them"""

    number_vms = 5
    number_updates = 5

    workspace_id = config.TEST_WORKSPACE_ID

    if workspace_id == "":
        # create the workspace to use
        payload = {
            "templateName": strings.BASE_WORKSPACE,
            "properties": {
                "display_name": "E2E test guacamole service",
                "description": "",
                "address_space_size": "small",
                "auth_type": "Manual",
                "client_id": f"{config.TEST_WORKSPACE_APP_ID}",
                "client_secret": f"{config.TEST_WORKSPACE_APP_SECRET}"
            }
        }

        admin_token = await get_admin_token(verify)
        workspace_path, workspace_id = await post_resource(payload, strings.API_WORKSPACES, admin_token, verify)
    else:
        workspace_path = f"/workspaces/{workspace_id}"

    workspace_owner_token, scope_uri = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)

    workspace_service_id = config.TEST_WORKSPACE_SERVICE_ID

    if workspace_service_id == "":
        # create a guac service
        service_payload = {
            "templateName": strings.GUACAMOLE_SERVICE,
            "properties": {
                "display_name": "Workspace service test",
                "description": ""
            }
        }

        workspace_service_path, _ = await post_resource(
            payload=service_payload,
            endpoint=f'/api{workspace_path}/{strings.API_WORKSPACE_SERVICES}',
            access_token=workspace_owner_token,
            verify=verify)
    else:
        workspace_service_path = f"{workspace_path}/{strings.API_WORKSPACE_SERVICES}/{workspace_service_id}"

    # Create the VMs in parallel, and wait for them to be created
    user_resource_payload = {
        "templateName": "tre-service-dev-vm",
        "properties": {
            "display_name": "Perf test VM",
            "description": "",
            "os_image": "Ubuntu 22.04 LTS",
            "admin_username": "researcher"
        }
    }

    tasks = []
    for i in range(number_vms):
        task = asyncio.create_task(post_resource(
            payload=user_resource_payload,
            endpoint=f'/api{workspace_service_path}/{strings.API_USER_RESOURCES}',
            access_token=workspace_owner_token,
            verify=verify))
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
            await post_resource(
                payload=patch_payload,
                endpoint=f'/api{resource_path}',
                access_token=workspace_owner_token,
                verify=verify,
                method="PATCH",
                wait=False)

        # clear up all the VMs in parallel
        # NOTE: Due to bug https://github.com/microsoft/AzureTRE/issues/1163 - this VM delete step currently fails
        task = asyncio.create_task(disable_and_delete_ws_resource(workspace_id, resource_path, verify))
        tasks.append(task)

    await asyncio.gather(*tasks)

    admin_token = await get_admin_token(verify)
    # clear up workspace + service (if we created them)
    if config.TEST_WORKSPACE_ID == "":
        await disable_and_delete_tre_resource(workspace_path, verify)
