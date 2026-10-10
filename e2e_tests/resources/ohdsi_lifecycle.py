"""Own OHDSI prerequisites until their dependent resources are removed."""

import asyncio
from builtins import BaseExceptionGroup
from contextlib import asynccontextmanager
from dataclasses import dataclass
import math
import os
import time
from uuid import UUID

from httpx import AsyncClient

from e2e_tests.bundle_evidence import record_operation, record_resource
from e2e_tests.conftest import get_workspace_owner_token
from e2e_tests.helpers import TIMEOUT, get_admin_token, get_auth_header, get_full_endpoint
from e2e_tests.resources.resource import disable_and_delete_resource
from e2e_tests.timeouts import cleanup_deadline

LIFECYCLE_SECONDS = 270 * 60
CLEANUP_RESERVE_SECONDS = 120 * 60
CREATE_SECONDS = 90 * 60
TERMINAL_STATES = {
    "deployed",
    "deployment_failed",
    "updated",
    "updating_failed",
    "deleted",
    "deleting_failed",
    "action_succeeded",
    "action_failed",
    "pipeline_succeeded",
    "pipeline_failed",
}
FAILED_STATES = {"deployment_failed", "updating_failed", "deleting_failed", "action_failed", "pipeline_failed"}


def lifecycle_deadlines():
    configured = os.environ.get("OHDSI_VALIDATION_DEADLINE", "")
    deadline = float(configured) if configured else time.time() + LIFECYCLE_SECONDS
    if not math.isfinite(deadline):
        raise ValueError("OHDSI validation deadline must be finite")
    remaining = min(LIFECYCLE_SECONDS, deadline - time.time())
    if remaining <= CLEANUP_RESERVE_SECONDS:
        raise TimeoutError("Insufficient OHDSI validation time remains after reserving cleanup")
    finish = asyncio.get_running_loop().time() + remaining
    return finish - CLEANUP_RESERVE_SECONDS, finish


def require_uuid(value):
    if not isinstance(value, str):
        raise ValueError("Resource identity must be a canonical, non-zero UUID")
    try:
        parsed = UUID(value)
    except ValueError:
        raise ValueError("Resource identity must be a canonical, non-zero UUID") from None
    if not parsed.int or str(parsed) != value:
        raise ValueError("Resource identity must be a canonical, non-zero UUID")
    return value


@dataclass
class OwnedResource:
    path: str
    identifier: str
    wrapper: str
    template: str
    display_name: str
    description: str
    workspace_id: str | None
    before_remove: object = None
    after_remove: object = None

    def validate(self, body):
        resource = body.get(self.wrapper, {})
        properties = resource.get("properties", {})
        if (
            resource.get("id") != self.identifier
            or resource.get("templateName") != self.template
            or properties.get("display_name") != self.display_name
            or properties.get("description") != self.description
            or not isinstance(resource.get("deploymentStatus"), str)
        ):
            raise ValueError("OHDSI resource ownership or deployment status changed")
        return resource


def creation_contract(payload, endpoint, workspace_id):
    if endpoint == "/api/workspaces" and workspace_id is None:
        wrapper, template = "workspace", "tre-workspace-base"
        if payload.get("properties", {}).get("auth_type") != "Automatic":
            raise ValueError("OHDSI validation needs a fresh Automatic workspace")
    elif workspace_id is not None and endpoint == f"/api/workspaces/{require_uuid(workspace_id)}/workspace-services":
        wrapper, template = "workspaceService", "tre-workspace-service-ohdsi"
        properties = payload.get("properties", {})
        if properties.get("configure_data_source") is not False or any(
            key in properties for key in ("data_source_config", "data_source_daimons")
        ):
            raise ValueError("OHDSI validation requires no external data source")
    else:
        raise ValueError("Unsupported OHDSI resource creation endpoint or parent")
    properties = payload.get("properties", {})
    if payload.get("templateName") != template or any(
        not isinstance(properties.get(name), str) or not properties[name].strip()
        for name in ("display_name", "description")
    ):
        raise ValueError("OHDSI creation needs the expected template and ownership properties")
    return wrapper, template


class OHDSIResources:
    def __init__(self, verify, work_finish, finish):
        self.verify = verify
        self.work_finish = work_finish
        self.finish = finish
        self.owned = []

    async def token(self, resource):
        if resource.workspace_id is not None:
            return await get_workspace_owner_token(resource.workspace_id, self.verify)
        return await get_admin_token(self.verify)

    async def create(self, payload, endpoint, workspace_id=None, *, after_remove=None, before_remove=None):
        wrapper, template = creation_contract(payload, endpoint, workspace_id)
        resource = OwnedResource(
            "",
            "",
            wrapper,
            template,
            payload["properties"]["display_name"],
            payload["properties"]["description"],
            workspace_id,
            before_remove,
            after_remove,
        )
        async with asyncio.timeout_at(min(self.work_finish, asyncio.get_running_loop().time() + CREATE_SECONDS)):
            token = await self.token(resource)
            async with AsyncClient(verify=self.verify, timeout=TIMEOUT) as client:
                response = await client.post(get_full_endpoint(endpoint), headers=get_auth_header(token), json=payload)
                if response.status_code != 202:
                    raise RuntimeError(f"OHDSI creation failed: HTTP {response.status_code}")
                operation = response.json()["operation"]
                resource_id = require_uuid(operation["resourceId"])
                resource_path = operation["resourcePath"]
                if resource_path != f"{endpoint.removeprefix('/api')}/{resource_id}":
                    raise ValueError("Accepted OHDSI resource has an unexpected path or parent")
                resource.path, resource.identifier = resource_path, resource_id
                # Own the accepted resource before evidence writes or client closure.
                self.owned.append(resource)
                operation_id = require_uuid(operation["id"])
                record_resource(payload, operation, "POST")
            result = await self.wait_terminal(resource, allow_absent=False, operation_id=operation_id)
            deployed, operations = result
            if deployed["deploymentStatus"] != "deployed" or any(
                operation["status"] in FAILED_STATES for operation in operations
            ):
                raise RuntimeError("OHDSI resource deployment or its pipeline failed")
        return resource.path, resource.identifier

    async def wait_terminal(self, resource, *, allow_absent=False, operation_id=None):
        endpoint = get_full_endpoint(f"/api{resource.path}")
        async with AsyncClient(verify=self.verify, timeout=TIMEOUT) as client:
            while True:
                response = await client.get(endpoint, headers=get_auth_header(await self.token(resource)))
                if response.status_code == 404 and allow_absent:
                    return None
                if response.status_code != 200:
                    raise RuntimeError(f"Could not inspect owned OHDSI resource: HTTP {response.status_code}")
                deployed = resource.validate(response.json())
                response = await client.get(
                    endpoint + "/operations", headers=get_auth_header(await self.token(resource))
                )
                if response.status_code != 200:
                    raise RuntimeError(f"Could not inspect OHDSI operations: HTTP {response.status_code}")
                operations = response.json()["operations"]
                if not isinstance(operations, list):
                    raise ValueError("OHDSI operations response must contain a list")
                for operation in operations:
                    observed_id = require_uuid(operation["id"])
                    record_operation(
                        f"/api{resource.path}/operations/{observed_id}",
                        operation["status"],
                        operation["status"] in TERMINAL_STATES,
                    )
                if (
                    (operation_id is None or any(o["id"] == operation_id for o in operations))
                    and deployed["deploymentStatus"] in TERMINAL_STATES
                    and operations
                    and all(operation["status"] in TERMINAL_STATES for operation in operations)
                ):
                    return deployed, operations
                await asyncio.sleep(30)

    async def upgrade(self, resource, overview):
        if resource.workspace_id is None:
            raise ValueError("Only the owned OHDSI service can be upgraded")
        deployed, _ = await self.wait_terminal(resource)
        headers = get_auth_header(await self.token(resource))
        headers["etag"] = deployed["_etag"]
        async with AsyncClient(verify=self.verify, timeout=TIMEOUT) as client:
            response = await client.patch(
                get_full_endpoint(f"/api{resource.path}"), headers=headers, json={"properties": {"overview": overview}}
            )
        if response.status_code != 202:
            raise RuntimeError(f"OHDSI upgrade failed: HTTP {response.status_code}")
        operation = response.json()["operation"]
        if operation["resourcePath"] != resource.path or operation["resourceId"] != resource.identifier:
            raise ValueError("OHDSI upgrade returned a different resource")
        operation_id = require_uuid(operation["id"])
        record_resource(None, operation, "PATCH")
        deployed, operations = await self.wait_terminal(resource, operation_id=operation_id)
        if deployed["deploymentStatus"] != "updated" or any(o["status"] in FAILED_STATES for o in operations):
            raise RuntimeError("OHDSI upgrade or its pipeline failed")
        assert deployed["properties"].get("overview") == overview, "OHDSI overview update was not preserved"
        return deployed

    async def assert_api_removed(self, resource):
        async with asyncio.timeout(5 * 60):
            async with AsyncClient(verify=self.verify, timeout=TIMEOUT) as client:
                while True:
                    response = await client.get(
                        get_full_endpoint(f"/api{resource.path}"),
                        headers=get_auth_header(await self.token(resource)),
                    )
                    if response.status_code == 404:
                        return
                    if response.status_code != 200:
                        raise RuntimeError(f"Could not verify OHDSI removal: HTTP {response.status_code}")
                    resource.validate(response.json())
                    await asyncio.sleep(10)

    async def remove(self, resource):
        present = await self.wait_terminal(resource, allow_absent=True)
        if present is not None:
            if resource.before_remove is not None:
                await resource.before_remove(resource.path, resource.identifier)
            await disable_and_delete_resource(
                f"/api{resource.path}", await self.token(resource), self.verify, allow_failed_disable=True
            )
            await self.assert_api_removed(resource)
        if resource.after_remove is not None:
            await resource.after_remove(resource.path, resource.identifier)

    async def close(self):
        failures = []
        while self.owned:
            seconds = (self.finish - asyncio.get_running_loop().time()) / len(self.owned)
            resource = self.owned.pop()
            try:
                if resource.workspace_id is None and failures:
                    raise RuntimeError("OHDSI workspace retained because service cleanup failed")
                async with cleanup_deadline(seconds):
                    await self.remove(resource)
            except (Exception, asyncio.CancelledError) as error:
                error.add_note(f"OHDSI validation cleanup failed for {resource.path}")
                failures.append(error)
        return failures


@asynccontextmanager
async def ohdsi_lifecycle(verify):
    work_finish, finish = lifecycle_deadlines()
    resources = OHDSIResources(verify, work_finish, finish)
    original = None
    async with cleanup_deadline(finish - asyncio.get_running_loop().time()):
        try:
            async with asyncio.timeout_at(work_finish):
                yield resources
        except BaseException as error:
            original = error
            raise
        finally:
            cleanup = asyncio.create_task(resources.close())
            cancelled = None
            while not cleanup.done():
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError as error:
                    cancelled = error
            failures = cleanup.result()
            failure = original if original is not None else cancelled
            if failure is not None:
                for error in failures:
                    failure.add_note(f"OHDSI cleanup also failed: {type(error).__name__}; {error.__notes__}")
            elif failures:
                raise BaseExceptionGroup("OHDSI resource cleanup failed", failures)
            if original is None and cancelled is not None:
                raise cancelled
