import asyncio
import pytest
import config
from resources.resource import disable_and_delete_resource, post_resource
from resources import strings

from helpers import get_admin_token

pytestmark = pytest.mark.asyncio


# TODO: tanya
@pytest.mark.skip
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
        if config.TEST_WORKSPACE_APP_PLAN != "":
            payload["properties"]["app_service_plan_sku"] = config.TEST_WORKSPACE_APP_PLAN

        admin_token = await get_admin_token(verify)
        task = asyncio.create_task(post_resource(payload=payload, endpoint=strings.API_WORKSPACES, access_token=admin_token, verify=verify))
        tasks.append(task)

    resource_paths = await asyncio.gather(*tasks)

    # Now disable + delete them all in parallel
    tasks = []
    for workspace_path, _ in resource_paths:
        task = asyncio.create_task(disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify))
        tasks.append(task)

    await asyncio.gather(*tasks)


@pytest.mark.extended
@pytest.mark.performance
@pytest.mark.timeout(3000)
async def test_bulk_updates_to_ensure_each_resource_updated_in_series(verify, setup_test_workspace_service) -> None:
    """Optionally creates a workspace and workspace service,
    then creates N number of VMs in parallel, patches each, and deletes them"""

    number_vms = 5
    number_updates = 5

    workspace_service_path, _, _, _, workspace_owner_token = setup_test_workspace_service

    # Create the VMs in parallel, and wait for them to be created
    user_resource_payload = {
        "templateName": strings.GUACAMOLE_WINDOWS_USER_RESOURCE,
        "properties": {
            "display_name": "Perf test VM",
            "description": "",
            "os_image": "Windows 10"
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
        task = asyncio.create_task(disable_and_delete_resource(f'/api{resource_path}', workspace_owner_token, verify))
        tasks.append(task)

    await asyncio.gather(*tasks)
