"""Upgrade a legacy Airlock workspace from an earlier release, then move it to Airlock v2.

The seed case runs on a TRE at an earlier release, before Airlock v2 existed. It creates a workspace with an
approved legacy import and keeps it. The verify case runs after the core upgrade with the current code. It
follows the documented procedure: the deployment runs `POST /migrations`, the workspace upgrade keeps the legacy
storage, and the change to `airlock_version` 2 moves the workspace.
"""

import asyncio
import logging
import os

import pytest

from e2e_tests import config
from e2e_tests.airlock import strings as airlock_strings
from e2e_tests.airlock.request import get_request, post_request, wait_for_status
from e2e_tests.conftest import clean_up_test_workspace, create_or_get_test_workspace, get_workspace_owner_token
from e2e_tests.helpers import get_admin_token
from e2e_tests.resources.resource import get_resource, post_resource
from e2e_tests.resources.sql_lifecycle import sql_lifecycle
from e2e_tests.resources.sql_probe import arm_client
from e2e_tests.test_airlock import create_draft_import_request_with_file, submit_airlock_import_request
from e2e_tests.test_airlock_migration import (
    LEGACY_ACCOUNTS,
    STORAGE_API,
    legacy_accounts,
    patch_status,
    require_review_roles,
    storage_account,
)

LOGGER = logging.getLogger(__name__)
SEED_NAME = "E2E Airlock upgrade seed"
# The core accounts of the legacy Airlock. `enable_legacy_airlock: false` deletes them.
CORE_LEGACY_ACCOUNTS = ("stalimex", "stalimip", "stalimrej", "stalimblocked", "stalexapp")


def require_test_app():
    if os.environ.get("AZURE_ENVIRONMENT", "AzureCloud") != "AzureCloud":
        raise ValueError("Airlock upgrade validation currently supports AzureCloud only")
    if not config.TEST_WORKSPACE_APP_ID or not config.TEST_WORKSPACE_APP_SECRET:
        raise ValueError("Airlock upgrade validation requires a configured manual test workspace application")


async def find_seed(admin_token, verify):
    """Return the seed workspace, or None. More than one seed workspace is an error."""
    workspaces = (await get_resource("/api/workspaces", admin_token, verify))["workspaces"]
    seeds = [w for w in workspaces if w["properties"].get("display_name") == SEED_NAME]
    if len(seeds) > 1:
        raise ValueError(f"Found {len(seeds)} Airlock upgrade seed workspaces")
    return seeds[0] if seeds else None


async def core_legacy_accounts():
    """Return the names of the core legacy accounts that exist."""
    tre = config.TRE_ID.replace("-", "")
    group = f"/subscriptions/{os.environ['ARM_SUBSCRIPTION_ID']}/resourceGroups/rg-{config.TRE_ID}"
    found = []
    async with arm_client() as arm:
        for prefix in CORE_LEGACY_ACCOUNTS:
            account_id = f"{group}/providers/Microsoft.Storage/storageAccounts/{prefix}{tre}"
            if await arm.request("GET", account_id, STORAGE_API, missing_ok=True) is not None:
                found.append(prefix)
    return found


async def approved_legacy_requests(workspace_path, token, verify):
    result = await get_request(f"/api{workspace_path}/requests", token, verify, 200)
    requests = [item["airlockRequest"] for item in result["airlockRequests"]]
    return [r for r in requests if r["status"] == airlock_strings.APPROVED_STATUS]


async def approve_legacy_import(workspace_path, token, verify):
    request_id, url = await submit_airlock_import_request(workspace_path, token, verify)
    assert storage_account(url) == f"stalimex{config.TRE_ID.replace('-', '')}"
    await post_request(
        {"approval": "True", "decisionExplanation": "Legacy import for the upgrade check"},
        f"/api{workspace_path}/requests/{request_id}/review",
        token,
        verify,
        200,
    )
    await wait_for_status(airlock_strings.APPROVED_STATUS, token, workspace_path, request_id, verify)
    return request_id


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.airlock_upgrade_seed
@pytest.mark.timeout(120 * 60)
async def test_seed_legacy_airlock_workspace(verify):
    require_test_app()
    admin_token = await get_admin_token(verify)
    if await find_seed(admin_token, verify) is not None:
        raise ValueError("An Airlock upgrade seed workspace already exists")
    workspace_path, workspace_id = await create_or_get_test_workspace(
        auth_type="Manual",
        verify=verify,
        client_id=config.TEST_WORKSPACE_APP_ID,
        client_secret=config.TEST_WORKSPACE_APP_SECRET,
        properties={"enable_airlock": True, "display_name": SEED_NAME},
    )
    try:
        token = await get_workspace_owner_token(workspace_id, verify)
        require_review_roles(token)
        request_id = await approve_legacy_import(workspace_path, token, verify)
        LOGGER.info("Seed workspace %s has the approved legacy import %s", workspace_id, request_id)
        assert await core_legacy_accounts() == list(CORE_LEGACY_ACCOUNTS)
        assert await legacy_accounts(workspace_id) == dict.fromkeys(LEGACY_ACCOUNTS, "Deny")
    except BaseException:
        # The verify case needs a complete seed. Do not keep a partial one.
        await clean_up_test_workspace("", workspace_path, verify)
        raise


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.airlock_upgrade_verify
@pytest.mark.timeout(285 * 60)
async def test_upgraded_legacy_workspace_moves_to_v2(verify):
    require_test_app()
    admin_token = await get_admin_token(verify)
    seed = await find_seed(admin_token, verify)
    if seed is None:
        raise ValueError("Run the airlock_upgrade_seed case on the earlier release first")
    workspace_id = seed["id"]
    workspace_path = f"/workspaces/{workspace_id}"
    async with sql_lifecycle(verify, deadline_variable="AIRLOCK_UPGRADE_VALIDATION_DEADLINE") as resources:
        resources.own(workspace_path, clean_up_test_workspace, "", workspace_path, verify)
        token = await get_workspace_owner_token(workspace_id, verify)
        require_review_roles(token)

        # The core upgrade kept the legacy storage, and the deployment stamped the workspace with version 1.
        assert await core_legacy_accounts() == list(CORE_LEGACY_ACCOUNTS)
        workspace = (await get_resource(f"/api{workspace_path}", token, verify))["workspace"]
        assert workspace["properties"]["airlock_version"] == 1
        old_version = workspace["templateVersion"]
        legacy_ids = [r["id"] for r in await approved_legacy_requests(workspace_path, token, verify)]
        assert len(legacy_ids) == 1, legacy_ids
        LOGGER.info("Seed workspace %s at template version %s", workspace_id, old_version)

        # The workspace upgrade keeps the legacy Airlock and its storage.
        template = await get_resource("/api/workspace-templates/tre-workspace-base", admin_token, verify)
        assert template["version"] != old_version
        async with asyncio.timeout(60 * 60):
            await post_resource(
                {"templateVersion": template["version"]},
                f"/api{workspace_path}",
                admin_token,
                verify,
                method="PATCH",
                etag=workspace["_etag"],
            )
        workspace = (await get_resource(f"/api{workspace_path}", token, verify))["workspace"]
        assert workspace["templateVersion"] == template["version"]
        assert workspace["properties"]["airlock_version"] == 1
        assert await legacy_accounts(workspace_id) == dict.fromkeys(LEGACY_ACCOUNTS, "Deny")
        LOGGER.info("The workspace upgrade from %s to %s kept the legacy storage", old_version, template["version"])

        # The upgraded workspace still uses the legacy Airlock.
        legacy_ids.append(await approve_legacy_import(workspace_path, token, verify))

        # The move to v2 deletes the legacy workspace storage and keeps the request records.
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
        assert await legacy_accounts(workspace_id) == dict.fromkeys(LEGACY_ACCOUNTS)
        for request_id in legacy_ids:
            legacy = (await get_request(f"/api{workspace_path}/requests/{request_id}", token, verify, 200))[
                "airlockRequest"
            ]
            assert legacy["status"] == airlock_strings.APPROVED_STATUS
            assert legacy["airlock_version"] == 1

        new_id, new_url = await create_draft_import_request_with_file(workspace_path, token, verify)
        assert storage_account(new_url) == f"stalairlock{config.TRE_ID.replace('-', '')}"
        await post_request(None, f"/api{workspace_path}/requests/{new_id}/cancel", token, verify, 200)
        assert await patch_status(workspace_path, {"airlock_version": 1}, admin_token, verify) == 400
        LOGGER.info("The upgraded workspace moved to Airlock v2")
