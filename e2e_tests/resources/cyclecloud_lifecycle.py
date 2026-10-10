"""Own a CycleCloud service before polling and reserve time for its deletion."""

import asyncio
from builtins import BaseExceptionGroup
from contextlib import asynccontextmanager
import math
import os
import time

from httpx import AsyncClient

from e2e_tests.bundle_evidence import record_operation, record_resource
from e2e_tests.helpers import TIMEOUT, get_admin_token, get_auth_header, get_full_endpoint
from e2e_tests.resources.cyclecloud import TEMPLATE, uuid_value
from e2e_tests.resources.resource import disable_and_delete_resource
from e2e_tests.timeouts import cleanup_deadline

LIFECYCLE_SECONDS = 270 * 60
CLEANUP_RESERVE_SECONDS = 120 * 60
TERMINAL = {
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
FAILED = {"deployment_failed", "updating_failed", "deleting_failed", "action_failed", "pipeline_failed"}


def lifecycle_deadlines():
    configured = os.environ.get("CYCLECLOUD_VALIDATION_DEADLINE", "")
    deadline = float(configured) if configured else time.time() + LIFECYCLE_SECONDS
    if not math.isfinite(deadline):
        raise ValueError("CycleCloud validation deadline must be finite")
    remaining = min(LIFECYCLE_SECONDS, deadline - time.time())
    if remaining <= CLEANUP_RESERVE_SECONDS:
        raise TimeoutError("Insufficient CycleCloud time remains after reserving cleanup")
    finish = asyncio.get_running_loop().time() + remaining
    return finish - CLEANUP_RESERVE_SECONDS, finish


class CycleCloudService:
    def __init__(self, verify, finish, payload, before_remove, after_remove):
        self.verify = verify
        self.finish = finish
        self.payload = payload
        self.path = None
        self.identifier = None
        self.before_remove = before_remove
        self.after_remove = after_remove

    def validate_owner(self, body):
        resource = body["sharedService"]
        if (
            resource["id"] != self.identifier
            or resource["templateName"] != TEMPLATE
            or any(
                resource["properties"].get(k) != self.payload["properties"][k] for k in ("display_name", "description")
            )
        ):
            raise ValueError("CycleCloud resource ownership changed")
        return resource

    async def headers(self):
        return get_auth_header(await get_admin_token(self.verify))

    async def create(self):
        if self.payload.get("templateName") != TEMPLATE or any(
            not self.payload.get("properties", {}).get(k) for k in ("display_name", "description")
        ):
            raise ValueError("CycleCloud creation needs the expected template and ownership properties")
        async with AsyncClient(verify=self.verify, timeout=TIMEOUT) as client:
            response = await client.post(
                get_full_endpoint("/api/shared-services"), headers=await self.headers(), json=self.payload
            )
            if response.status_code != 202:
                raise RuntimeError(f"CycleCloud creation failed: HTTP {response.status_code}")
            operation = response.json()["operation"]
            identifier = uuid_value(operation["resourceId"])
            path = operation["resourcePath"]
            if path != f"/shared-services/{identifier}":
                raise ValueError("Accepted CycleCloud resource has an unexpected path")
            self.path, self.identifier = path, identifier
            # Own the accepted resource before evidence writes or client closure.
            record_resource(self.payload, operation, "POST")
        resource, operations = await self.wait_terminal()
        if resource["deploymentStatus"] != "deployed" or any(o["status"] in FAILED for o in operations):
            raise RuntimeError("CycleCloud deployment or firewall pipeline failed")
        return resource

    async def wait_terminal(self, *, allow_absent=False, operation_id=None):
        endpoint = get_full_endpoint(f"/api{self.path}")
        async with AsyncClient(verify=self.verify, timeout=TIMEOUT) as client:
            while True:
                response = await client.get(endpoint, headers=await self.headers())
                if response.status_code == 404 and allow_absent:
                    return None
                if response.status_code != 200:
                    raise RuntimeError(f"Could not inspect CycleCloud resource: HTTP {response.status_code}")
                resource = self.validate_owner(response.json())
                response = await client.get(endpoint + "/operations", headers=await self.headers())
                if response.status_code != 200:
                    raise RuntimeError(f"Could not inspect CycleCloud operations: HTTP {response.status_code}")
                operations = response.json()["operations"]
                if not isinstance(operations, list):
                    raise ValueError("CycleCloud operations must be a list")
                for operation in operations:
                    uuid_value(operation["id"])
                    record_operation(
                        f"/api{self.path}/operations/{operation['id']}",
                        operation["status"],
                        operation["status"] in TERMINAL,
                    )
                expected_seen = operation_id is None or any(o["id"] == operation_id for o in operations)
                if (
                    expected_seen
                    and operations
                    and resource["deploymentStatus"] in TERMINAL
                    and all(o["status"] in TERMINAL for o in operations)
                ):
                    return resource, operations
                await asyncio.sleep(15)

    async def change(self, *, action=None, overview=None):
        if action not in (None, "start", "stop") or (action is not None) == (overview is not None):
            raise ValueError("Select one supported CycleCloud action or a metadata update")
        resource, _ = await self.wait_terminal()
        endpoint = get_full_endpoint(f"/api{self.path}")
        headers = await self.headers()
        headers["etag"] = resource["_etag"]
        async with AsyncClient(verify=self.verify, timeout=TIMEOUT) as client:
            if action:
                response = await client.post(endpoint + "/invoke-action", headers=headers, params={"action": action})
            else:
                response = await client.patch(endpoint, headers=headers, json={"properties": {"overview": overview}})
        if response.status_code != 202:
            raise RuntimeError(f"CycleCloud mutation failed: HTTP {response.status_code}")
        operation = response.json()["operation"]
        if operation["resourcePath"] != self.path or operation["resourceId"] != self.identifier:
            raise ValueError("CycleCloud mutation returned a different resource")
        operation_id = uuid_value(operation["id"])
        record_resource(None, operation, "POST" if action else "PATCH")
        result, operations = await self.wait_terminal(operation_id=operation_id)
        observed = next(o for o in operations if o["id"] == operation_id)
        if observed["status"] in FAILED or result["deploymentStatus"] in FAILED:
            raise RuntimeError("CycleCloud mutation or its pipeline failed")
        if overview is not None and result["properties"].get("overview") != overview:
            raise AssertionError("CycleCloud metadata update was not preserved")
        return result

    async def close(self):
        if self.path is None:
            return []
        try:
            async with cleanup_deadline(self.finish - asyncio.get_running_loop().time()):
                if await self.wait_terminal(allow_absent=True) is not None:
                    await self.before_remove(self.identifier)
                    await disable_and_delete_resource(
                        f"/api{self.path}", await get_admin_token(self.verify), self.verify, allow_failed_disable=True
                    )
                    async with AsyncClient(verify=self.verify, timeout=TIMEOUT) as client:
                        while True:
                            response = await client.get(
                                get_full_endpoint(f"/api{self.path}"), headers=await self.headers()
                            )
                            if response.status_code == 404:
                                break
                            if response.status_code != 200:
                                raise RuntimeError(f"Could not verify CycleCloud deletion: HTTP {response.status_code}")
                            self.validate_owner(response.json())
                            await asyncio.sleep(10)
                await self.after_remove(self.identifier)
        except (Exception, asyncio.CancelledError) as error:
            error.add_note(f"CycleCloud cleanup failed for {self.path}")
            return [error]
        return []


@asynccontextmanager
async def cyclecloud_lifecycle(verify, payload, before_remove, after_remove):
    work_finish, finish = lifecycle_deadlines()
    resource = CycleCloudService(verify, finish, payload, before_remove, after_remove)
    original = None
    try:
        async with asyncio.timeout_at(work_finish):
            yield resource
    except BaseException as error:
        original = error
        raise
    finally:
        cleanup = asyncio.create_task(resource.close())
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
                failure.add_note(f"CycleCloud cleanup also failed: {type(error).__name__}; {error.__notes__}")
        elif failures:
            raise BaseExceptionGroup("CycleCloud cleanup failed", failures)
        if original is None and cancelled is not None:
            raise cancelled
