import pytest

from helpers import get_admin_token
from resources.workspace import get_workspace_auth_details

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.manual_app
async def test_manually_created_application_workspace(setup_manually_created_application_workspace, verify) -> None:
    """Ensure a manually created workspace application continues to work for manual auth flows."""
    workspace_path, workspace_id = setup_manually_created_application_workspace

    admin_token = await get_admin_token(verify=verify)
    workspace_owner_token, scope_uri = await get_workspace_auth_details(
        admin_token=admin_token,
        workspace_id=workspace_id,
        verify=verify)

    assert workspace_owner_token, "Expected a workspace owner token for manually created app"
    assert scope_uri.startswith("api://"), "Scope URI should be an api:// identifier"
