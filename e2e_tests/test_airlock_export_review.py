"""Validate export review using synthetic data uploaded inside its workspace."""

import asyncio
import base64
from contextlib import AsyncExitStack, asynccontextmanager
import json
import math
import os
import time
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import pytest

from e2e_tests import config
from e2e_tests.bundle_evidence import record_deployed_resource
from e2e_tests.run_bundle import load_catalog
from e2e_tests.airlock import strings as airlock_strings
from e2e_tests.airlock.request import get_request, post_request, wait_for_status
from e2e_tests.conftest import (
    clean_up_test_workspace,
    clean_up_test_workspace_service,
    create_or_get_test_workspace,
    create_or_get_test_workpace_service,
    get_workspace_owner_token,
)
from e2e_tests.helpers import get_admin_token, get_auth_header
from e2e_tests.resources import strings
from e2e_tests.resources.airlock_probe import run_probe
from e2e_tests.resources.nexus import nexus_prerequisites
from e2e_tests.resources.resource import get_resource, post_resource, temporary_resource
from e2e_tests.resources.sql_probe import COMPUTE_API, arm_client, validate_vm
from e2e_tests.test_airlock import managed_review_vm, wait_for_review_vm_deletion
from e2e_tests.timeouts import cleanup_deadline

LIFECYCLE_SECONDS = 270 * 60
CLEANUP_RESERVE_SECONDS = 120 * 60
REVIEW_TEMPLATE = "tre-service-guacamole-export-reviewvm"
VM_PAYLOAD = {
    "templateName": strings.GUACAMOLE_WINDOWS_USER_RESOURCE,
    "properties": {
        "display_name": "Airlock export test client",
        "description": "Temporary synthetic export data uploader",
        "os_image": "Windows 11",
        "vm_size": "2 CPU | 8GB RAM",
        "admin_username": "researcher",
        "shared_storage_access": False,
        **{
            f"install_{tool}": False
            for tool in ("azure_cli", "vscode", "storage_explorer", "git", "python_tools", "r_tools")
        },
    },
}


def require_export_roles(token):
    # This is a prerequisite diagnostic. The API validates the token and roles.
    try:
        encoded = get_auth_header(token)["Authorization"].split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        roles = claims.get("roles", [])
        if not isinstance(roles, list) or not {"WorkspaceOwner", "AirlockManager"}.issubset(roles):
            raise ValueError
    except (ValueError, IndexError, TypeError, AttributeError):
        raise ValueError(
            "Export validation requires WorkspaceOwner and AirlockManager on the test workspace app"
        ) from None


class ExportResources(AsyncExitStack):
    """Give each owned resource a share of the remaining cleanup time."""

    def __init__(self, finish):
        super().__init__()
        self.finish = finish
        self.pending = 0

    async def close_one(self, callback, *args, **kwargs):
        seconds = (self.finish - asyncio.get_running_loop().time()) / self.pending
        try:
            async with cleanup_deadline(seconds):
                return await callback(*args, **kwargs)
        finally:
            self.pending -= 1

    def push_async_callback(self, callback, *args, **kwargs):
        self.pending += 1
        return super().push_async_callback(self.close_one, callback, *args, **kwargs)

    async def enter_async_context(self, context):
        result = await context.__aenter__()
        self.pending += 1

        async def exit_context(*args):
            return await self.close_one(context.__aexit__, *args)

        self.push_async_exit(exit_context)
        return result


@asynccontextmanager
async def export_resources(verify):
    """Keep dependency cleanup outside the work deadline and within the job budget."""
    if os.environ.get("AZURE_ENVIRONMENT", "AzureCloud") != "AzureCloud":
        raise ValueError("Export review validation currently supports AzureCloud only")
    if not config.TEST_WORKSPACE_APP_ID or not config.TEST_WORKSPACE_APP_SECRET:
        raise ValueError("Export review validation requires a configured manual test workspace application")
    configured = os.environ.get("EXPORT_REVIEW_VALIDATION_DEADLINE", "")
    deadline = float(configured) if configured else time.time() + LIFECYCLE_SECONDS
    if not math.isfinite(deadline):
        raise ValueError("Export review deadline must be finite")
    remaining = min(LIFECYCLE_SECONDS, deadline - time.time())
    if remaining <= CLEANUP_RESERVE_SECONDS:
        raise TimeoutError("Insufficient export review time remains after reserving cleanup")
    resources = ExportResources(asyncio.get_running_loop().time() + remaining)
    original = None
    async with cleanup_deadline(remaining):
        try:
            async with asyncio.timeout(remaining - CLEANUP_RESERVE_SECONDS):
                async with asyncio.timeout(60 * 60):
                    await resources.enter_async_context(nexus_prerequisites(verify))
                yield resources
        except BaseException as error:
            original = error
            raise
        finally:
            # Pass the original failure to resource owners and finish their bounded
            # cleanup even if the caller cancels more than once.
            cleanup = asyncio.create_task(
                resources.__aexit__(
                    type(original) if original else None, original, getattr(original, "__traceback__", None)
                )
            )
            cancelled = None
            while not cleanup.done():
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError as error:
                    cancelled = error
                except Exception:
                    break
            try:
                cleanup.result()
            except (Exception, asyncio.CancelledError) as error:
                if original is None and cancelled is None:
                    raise
                (original or cancelled).add_note(f"Export review cleanup also failed: {error!r}")
            if original is None and cancelled is not None:
                raise cancelled


async def owned_vm(arm, resource_path, template, workspace_id, service_id, token, verify):
    record = (await get_resource(f"/api{resource_path}", token, verify))["userResource"]
    assert record["templateName"] == template
    assert record["deploymentStatus"] == "deployed"
    record_deployed_resource(record, resource_path)
    assert record["templateVersion"] == load_catalog()[template]["source_version"], (
        "The deployed VM bundle version differs from this checkout"
    )
    resource_id = resource_path.rsplit("/", 1)[1]
    assert record["id"] == resource_id
    assert resource_path == f"/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}"
    properties = record["properties"]
    vm_id = properties["azure_resource_id"]
    vm = await arm.request("GET", vm_id, COMPUTE_API)
    subscription = properties.get("workspace_subscription_id") or os.environ["ARM_SUBSCRIPTION_ID"]
    validate_vm(vm, vm_id, subscription, config.TRE_ID, workspace_id, service_id, resource_id)
    return vm_id, vm["location"]


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.export_review_validation
@pytest.mark.nexus_required
async def test_airlock_export_review_vm_flow(verify):
    async with export_resources(verify) as resources:
        # A separate workspace avoids changes to pre-created or import-test resources.
        workspace_path, workspace_id = await create_or_get_test_workspace(
            auth_type="Manual",
            verify=verify,
            pre_created_workspace_id="",
            client_id=config.TEST_WORKSPACE_APP_ID,
            client_secret=config.TEST_WORKSPACE_APP_SECRET,
        )
        resources.push_async_callback(clean_up_test_workspace, "", workspace_path, verify)
        token = await get_workspace_owner_token(workspace_id, verify)
        require_export_roles(token)
        service_path, service_id = await create_or_get_test_workpace_service(workspace_path, token, "", verify)
        resources.push_async_callback(clean_up_test_workspace_service, "", service_path, workspace_id, verify)
        workspace = (await get_resource(f"/api{workspace_path}", token, verify))["workspace"]
        assert workspace["properties"].get("airlock_version") == 2, "Export validation requires Airlock v2"
        review_config = dict(workspace["properties"].get("airlock_review_config") or {})
        review_config["export"] = {
            "export_vm_workspace_service_id": service_id,
            "export_vm_user_resource_template_name": REVIEW_TEMPLATE,
        }
        async with asyncio.timeout(30 * 60):
            await post_resource(
                {
                    "properties": {
                        "enable_airlock": True,
                        "configure_review_vms": True,
                        "airlock_review_config": review_config,
                    }
                },
                f"/api{workspace_path}",
                await get_admin_token(verify),
                verify,
                method="PATCH",
                etag=workspace["_etag"],
            )
        async with asyncio.timeout(45 * 60):
            seed_path = await resources.enter_async_context(
                temporary_resource(VM_PAYLOAD, f"/api{service_path}/user-resources", token, verify)
            )
        async with arm_client() as arm:
            seed_vm, seed_location = await owned_vm(
                arm, seed_path, strings.GUACAMOLE_WINDOWS_USER_RESOURCE, workspace_id, service_id, token, verify
            )
            result = await post_request(
                {"type": airlock_strings.EXPORT, "businessJustification": "E2E synthetic export review validation"},
                f"/api{workspace_path}/requests",
                token,
                verify,
                201,
            )
            request = result["airlockRequest"]
            assert request["type"] == airlock_strings.EXPORT
            assert request["status"] == airlock_strings.DRAFT_STATUS
            request_id = str(UUID(request["id"]))
            endpoint = f"/api{workspace_path}/requests/{request_id}"
            container_url = (await get_request(endpoint + "/link", token, verify, 200))["containerUrl"]
            url = urlsplit(container_url)
            if (
                url.hostname != f"stalairlockg{config.TRE_ID.replace('-', '')}.blob.core.windows.net"
                or url.path != f"/{request_id}-draft"
            ):
                raise ValueError("Unexpected export draft storage or container")
            probe_id = uuid4().hex
            probe = dict(
                probe_id=probe_id, blob_name=f"export-{probe_id}.txt", content=f"Synthetic export review {probe_id}\n"
            )
            await run_probe(arm, seed_vm, seed_location, phase="upload", container_url=container_url, **probe)
            submitted = await post_request(None, endpoint + "/submit", token, verify, 200)
            assert submitted["airlockRequest"]["status"] == airlock_strings.SUBMITTED_STATUS
            async with asyncio.timeout(15 * 60):
                await wait_for_status(airlock_strings.IN_REVIEW_STATUS, token, workspace_path, request_id, verify)
            async with managed_review_vm(workspace_path, request_id, token, token, verify) as review_path:
                review_vm, review_location = await owned_vm(
                    arm, review_path, REVIEW_TEMPLATE, workspace_id, service_id, token, verify
                )
                await run_probe(arm, review_vm, review_location, phase="read", **probe)
                await post_request(
                    {"approval": True, "decisionExplanation": "Synthetic export data matched the expected hash"},
                    endpoint + "/review",
                    token,
                    verify,
                    200,
                )
                async with asyncio.timeout(15 * 60):
                    await wait_for_status(airlock_strings.APPROVED_STATUS, token, workspace_path, request_id, verify)
                await wait_for_review_vm_deletion(review_path, token, verify)
