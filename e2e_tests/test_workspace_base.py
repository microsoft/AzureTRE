"""An opt-in base-workspace case with its own provisioning and cleanup evidence."""

import asyncio

import pytest
from httpx import AsyncClient
from starlette import status

from e2e_tests.conftest import clean_up_test_workspace, create_or_get_test_workspace
from e2e_tests.helpers import TIMEOUT, get_admin_token, get_auth_header, get_full_endpoint
from e2e_tests.resources import strings
from e2e_tests.resources.workspace import get_workspace, get_workspace_auth_details
from e2e_tests.timeouts import cleanup_deadline

pytestmark = pytest.mark.asyncio(loop_scope="session")
BODY_TIMEOUT_SECONDS = 5 * 60
CLEANUP_TIMEOUT_SECONDS = 60 * 60


async def delete_and_check_workspace(workspace_path, verify):
    async with cleanup_deadline(CLEANUP_TIMEOUT_SECONDS):
        await clean_up_test_workspace(pre_created_workspace_id="", workspace_path=workspace_path, verify=verify)
        admin_token = await get_admin_token(verify)
        async with AsyncClient(verify=verify) as client:
            response = await client.get(
                get_full_endpoint(f"/api{workspace_path}"), headers=get_auth_header(admin_token), timeout=TIMEOUT
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            f"Workspace remains visible after uninstall: HTTP {response.status_code}"
        )


@pytest.mark.workspace_validation
async def test_base_workspace_lifecycle(verify):
    # Always create an owned workspace, even when other suites reuse configured IDs.
    workspace_path, workspace_id = await create_or_get_test_workspace(
        auth_type="Automatic", verify=verify, template_name=strings.BASE_WORKSPACE, pre_created_workspace_id=""
    )
    try:
        async with asyncio.timeout(BODY_TIMEOUT_SECONDS):
            admin_token = await get_admin_token(verify)
            async with AsyncClient(verify=verify) as client:
                workspace = await get_workspace(client, workspace_id, get_auth_header(admin_token))
                assert workspace["id"] == workspace_id
                assert workspace["templateName"] == strings.BASE_WORKSPACE
                assert workspace["deploymentStatus"] == strings.RESOURCE_STATUS_DEPLOYED
                assert workspace["isEnabled"] is True

                workspace_token, _ = await get_workspace_auth_details(admin_token, workspace_id, verify)
                response = await client.get(
                    get_full_endpoint(f"/api{workspace_path}/workspace-services"),
                    headers=get_auth_header(workspace_token),
                    timeout=TIMEOUT,
                )
                assert response.status_code == status.HTTP_200_OK, (
                    f"Workspace identity cannot list services: HTTP {response.status_code}"
                )
                assert response.json()["workspaceServices"] == [], "New workspace contains unexpected services"
    except BaseException as original_error:
        try:
            await delete_and_check_workspace(workspace_path, verify)
        except Exception as cleanup_error:
            original_error.add_note(f"Workspace cleanup also failed: {cleanup_error!r}")
        raise
    else:
        await delete_and_check_workspace(workspace_path, verify)
