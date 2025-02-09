import pytest

from httpx import AsyncClient
from starlette import status

import config
from e2e_tests.conftest import clean_up_test_workspace, create_or_get_test_workspace
from e2e_tests.resources.workspace import get_workspace
from helpers import assert_status, get_auth_header, get_template
from resources import strings
from helpers import get_admin_token


pytestmark = pytest.mark.asyncio(loop_scope="session")


workspace_templates = [
    (strings.BASE_WORKSPACE)
]

workspace_templates_test_create = [
    # Base workspace template is excluded as covered by other extended tests
    (strings.UNRESTRICTED_WORKSPACE),
    (strings.AIRLOCK_IMPORT_REVIEW_WORKSPACE)
]


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_templates)
async def test_get_workspace_templates(template_name, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        admin_token = await get_admin_token(verify)
        response = await client.get(f"{config.TRE_URL}{strings.API_WORKSPACE_TEMPLATES}", headers=get_auth_header(admin_token))

        template_names = [templates["name"] for templates in response.json()["templates"]]
        assert (template_name in template_names), f"No {template_name} template found"


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_templates)
async def test_get_workspace_template(template_name, verify) -> None:
    admin_token = await get_admin_token(verify)
    async with get_template(template_name, strings.API_WORKSPACE_TEMPLATES, admin_token, verify) as response:
        assert_status(response, [status.HTTP_200_OK], f"Failed to GET template: {template_name}")


@pytest.mark.extended
@pytest.mark.parametrize("template_name", workspace_templates_test_create)
async def test_create_workspace_templates(template_name, verify) -> None:

    workspace_path, workspace_id = await create_or_get_test_workspace(auth_type="Automatic", verify=verify, template_name=template_name)

    async with AsyncClient(verify=verify) as client:
        admin_token = await get_admin_token(verify=verify)
        auth_headers = get_auth_header(admin_token)
        workspace = await get_workspace(client, workspace_id, auth_headers)

        assert workspace["deploymentStatus"] == strings.RESOURCE_STATUS_DEPLOYED

    # Tear-down in a cascaded way
    await clean_up_test_workspace(pre_created_workspace_id="", workspace_path=workspace_path, verify=verify)
