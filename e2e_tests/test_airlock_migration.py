"""Move a legacy Airlock workspace to Airlock v2 with the documented procedure."""

import asyncio
import base64
import json
import logging
import os
from urllib.parse import urlsplit

from httpx import AsyncClient
import pytest

from e2e_tests import config
from e2e_tests.airlock import strings as airlock_strings
from e2e_tests.airlock.request import get_request, post_request, wait_for_status
from e2e_tests.conftest import clean_up_test_workspace, create_or_get_test_workspace, get_workspace_owner_token
from e2e_tests.helpers import get_admin_token, get_auth_header, get_full_endpoint
from e2e_tests.resources.resource import get_resource, post_resource
from e2e_tests.resources.sql_lifecycle import sql_lifecycle
from e2e_tests.test_airlock import create_draft_import_request_with_file, submit_airlock_import_request

LOGGER = logging.getLogger(__name__)


def require_review_roles(token):
    # This is a prerequisite diagnostic. The API validates the token and roles.
    try:
        encoded = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        roles = claims.get("roles", [])
        if not isinstance(roles, list) or not {"WorkspaceOwner", "AirlockManager"}.issubset(roles):
            raise ValueError
    except (ValueError, IndexError, TypeError, AttributeError):
        raise ValueError(
            "Airlock migration validation requires WorkspaceOwner and AirlockManager on the test workspace app"
        ) from None


def storage_account(container_url):
    return urlsplit(container_url).hostname.split(".", 1)[0]


async def patch_status(workspace_path, properties, token, verify):
    """Send a workspace PATCH and return its HTTP status, without waiting for an operation."""
    workspace = (await get_resource(f"/api{workspace_path}", token, verify))["workspace"]
    headers = get_auth_header(token) | {"etag": workspace["_etag"]}
    async with AsyncClient(verify=verify, timeout=60) as client:
        response = await client.patch(
            get_full_endpoint(f"/api{workspace_path}"), headers=headers, json={"properties": properties}
        )
    return response.status_code


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.airlock_migration_validation
@pytest.mark.timeout(285 * 60)
async def test_legacy_airlock_workspace_moves_to_v2(verify):
    if os.environ.get("AZURE_ENVIRONMENT", "AzureCloud") != "AzureCloud":
        raise ValueError("Airlock migration validation currently supports AzureCloud only")
    if not config.TEST_WORKSPACE_APP_ID or not config.TEST_WORKSPACE_APP_SECRET:
        raise ValueError("Airlock migration validation requires a configured manual test workspace application")
    tre = config.TRE_ID.replace("-", "")
    async with sql_lifecycle(verify, deadline_variable="AIRLOCK_MIGRATION_VALIDATION_DEADLINE") as resources:
        workspace_path, workspace_id = await create_or_get_test_workspace(
            auth_type="Manual",
            verify=verify,
            client_id=config.TEST_WORKSPACE_APP_ID,
            client_secret=config.TEST_WORKSPACE_APP_SECRET,
            properties={"enable_airlock": True, "airlock_version": 1},
        )
        resources.own(workspace_path, clean_up_test_workspace, "", workspace_path, verify)
        token = await get_workspace_owner_token(workspace_id, verify)
        require_review_roles(token)
        admin_token = await get_admin_token(verify)
        workspace = (await get_resource(f"/api{workspace_path}", token, verify))["workspace"]
        assert workspace["properties"]["airlock_version"] == 1

        # Legacy behaviour: an import uses the legacy external account and completes.
        legacy_id, legacy_url = await submit_airlock_import_request(workspace_path, token, verify)
        assert storage_account(legacy_url) == f"stalimex{tre}"
        await post_request(
            {"approval": "True", "decisionExplanation": "Legacy import before the move to v2"},
            f"/api{workspace_path}/requests/{legacy_id}/review",
            token,
            verify,
            200,
        )
        await wait_for_status(airlock_strings.APPROVED_STATUS, token, workspace_path, legacy_id, verify)
        LOGGER.info("A legacy import passed in the v1 workspace")

        # The migration stamps pre-v2 workspaces. A second call must change nothing.
        for attempt in (1, 2):
            result = await post_request(None, "/api/migrations", admin_token, verify, 202)
            LOGGER.info("Migration call %d: %s", attempt, result["migrations"])
            workspace = (await get_resource(f"/api{workspace_path}", token, verify))["workspace"]
            assert workspace["properties"]["airlock_version"] == 1

        # A request in progress blocks the move, so that its data is not left in legacy storage.
        draft_id, draft_url = await create_draft_import_request_with_file(workspace_path, token, verify)
        assert storage_account(draft_url) == f"stalimex{tre}"
        assert await patch_status(workspace_path, {"airlock_version": 2}, admin_token, verify) == 400
        await post_request(None, f"/api{workspace_path}/requests/{draft_id}/cancel", token, verify, 200)

        workspace = (await get_resource(f"/api{workspace_path}", token, verify))["workspace"]
        async with asyncio.timeout(60 * 60):
            await post_resource(
                {"properties": {"airlock_version": 2}},
                f"/api{workspace_path}",
                admin_token,
                verify,
                method="PATCH",
                etag=workspace["_etag"],
            )
        workspace = (await get_resource(f"/api{workspace_path}", token, verify))["workspace"]
        assert workspace["properties"]["airlock_version"] == 2
        LOGGER.info("The workspace moved to Airlock v2")

        # V2 behaviour: a new request uses the consolidated core account and its own draft container.
        new_id, new_url = await create_draft_import_request_with_file(workspace_path, token, verify)
        assert storage_account(new_url) == f"stalairlock{tre}"
        assert urlsplit(new_url).path == f"/{new_id}-draft"
        new_request = (await get_request(f"/api{workspace_path}/requests/{new_id}", token, verify, 200))[
            "airlockRequest"
        ]
        assert new_request["airlock_version"] == 2
        await post_request(None, f"/api{workspace_path}/requests/{new_id}/cancel", token, verify, 200)

        # The legacy request keeps its record and its version. The move deletes its stored files, as documented.
        legacy = (await get_request(f"/api{workspace_path}/requests/{legacy_id}", token, verify, 200))["airlockRequest"]
        assert legacy["status"] == airlock_strings.APPROVED_STATUS
        assert legacy["airlock_version"] == 1

        # A downgrade would remove access to data that v2 keeps.
        assert await patch_status(workspace_path, {"airlock_version": 1}, admin_token, verify) == 400
        LOGGER.info("The API refused the move back to Airlock v1")
