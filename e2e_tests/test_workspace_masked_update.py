"""A sensitive workspace property stays masked after an update.

The case creates a workspace with the manual test application. A TRE admin then updates the client secret two
times with the same value, and the workspace token reads the workspace and its history back. The case logs only
true or false values and counts. It never logs a property value or a response text.
"""

import base64
import json
import logging

import pytest
from httpx import AsyncClient

from e2e_tests import config
from e2e_tests.conftest import clean_up_test_workspace, create_or_get_test_workspace, get_workspace_owner_token
from e2e_tests.helpers import get_admin_token, get_auth_header, get_full_endpoint
from e2e_tests.resources import strings
from e2e_tests.resources.deployment import patch_done
from e2e_tests.resources.resource import wait_for

LOGGER = logging.getLogger(__name__)
SENSITIVE = "client_secret"
MASK = "REDACTED"


def token_roles(provider) -> list:
    """Read the role names from the token. The names are not secret."""
    payload = provider.get_token().split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    return sorted(claims.get("roles", []))


async def read_workspace(client, workspace_path, token) -> dict:
    response = await client.get(get_full_endpoint(f"/api{workspace_path}"), headers=get_auth_header(token))
    assert response.status_code == 200, f"The workspace GET returned {response.status_code}"
    value = response.json()["workspace"]["properties"].get(SENSITIVE)
    return {"masked": value == MASK, "equal_to_update": value == config.TEST_WORKSPACE_APP_SECRET}


async def read_history(client, workspace_path, token) -> dict:
    response = await client.get(get_full_endpoint(f"/api{workspace_path}/history"), headers=get_auth_header(token))
    assert response.status_code == 200, f"The workspace history GET returned {response.status_code}"
    values = [item["properties"].get(SENSITIVE) for item in response.json()["resource_history"]]
    return {
        "items": len(values),
        "masked": sum(value == MASK for value in values),
        "equal_to_update": sum(value == config.TEST_WORKSPACE_APP_SECRET for value in values),
    }


async def update_sensitive_property(client, workspace_path, admin_token) -> str:
    payload = {
        "properties": {
            "auth_type": "Manual",
            "client_id": config.TEST_WORKSPACE_APP_ID,
            "client_secret": config.TEST_WORKSPACE_APP_SECRET,
        }
    }
    headers = {**get_auth_header(admin_token), "eTag": "*"}
    response = await client.patch(get_full_endpoint(f"/api{workspace_path}"), headers=headers, json=payload)
    # Do not log the response text. A validation error can repeat the request values.
    assert response.status_code == 202, f"The workspace PATCH returned {response.status_code}"
    return response.headers["Location"]


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.masking_validation
@pytest.mark.timeout(150 * 60)
async def test_a_sensitive_property_stays_masked_after_an_update(verify):
    if not (config.TEST_WORKSPACE_APP_ID and config.TEST_WORKSPACE_APP_SECRET):
        pytest.skip("The case needs the manual test workspace application")

    workspace_path, workspace_id = await create_or_get_test_workspace(
        auth_type="Manual",
        verify=verify,
        client_id=config.TEST_WORKSPACE_APP_ID,
        client_secret=config.TEST_WORKSPACE_APP_SECRET,
    )
    try:
        admin_token = await get_admin_token(verify)
        workspace_token = await get_workspace_owner_token(workspace_id, verify)
        LOGGER.info("Roles in the workspace token: %s", token_roles(workspace_token))

        results = {}
        async with AsyncClient(verify=verify, timeout=60.0) as client:
            results["after_install"] = await read_workspace(client, workspace_path, workspace_token)
            for update in (1, 2):
                operation = await update_sensitive_property(client, workspace_path, admin_token)
                # The API writes the properties before it sends the update, so read them at once.
                results[f"after_update_{update}"] = await read_workspace(client, workspace_path, workspace_token)
                await wait_for(patch_done, client, operation, admin_token, [strings.RESOURCE_STATUS_UPDATING_FAILED])
            results["after_operations"] = await read_workspace(client, workspace_path, workspace_token)
            results["history"] = await read_history(client, workspace_path, workspace_token)
        LOGGER.info("Masking of the sensitive property: %s", results)

        assert results["after_install"]["masked"], "The workspace response does not mask the property after an install"
        updates = [results[name]["masked"] for name in ("after_update_1", "after_update_2", "after_operations")]
        assert all(updates), "The workspace response does not mask the property after an update"
        assert results["history"]["equal_to_update"] == 0, "The workspace history does not mask the property"
    finally:
        await clean_up_test_workspace(pre_created_workspace_id="", workspace_path=workspace_path, verify=verify)
