"""Keep AML resources and failed-create recovery inside one bounded lifetime."""

import asyncio
from builtins import BaseExceptionGroup
from contextlib import asynccontextmanager
from functools import partial
import math
import os
import time

from httpx import AsyncClient

from e2e_tests.conftest import create_or_get_test_workspace, get_workspace_owner_token
from e2e_tests.helpers import TIMEOUT, get_admin_token, get_auth_header, get_full_endpoint
from e2e_tests.resources.aml import assert_removed
from e2e_tests.resources.resource import disable_and_delete_resource, post_resource
from e2e_tests.timeouts import cleanup_deadline

LIFECYCLE_SECONDS = 270 * 60
CLEANUP_RESERVE_SECONDS = 120 * 60


def lifecycle_deadlines():
    configured = os.environ.get("AML_VALIDATION_DEADLINE", "")
    deadline = float(configured) if configured else time.time() + LIFECYCLE_SECONDS
    if not math.isfinite(deadline):
        raise ValueError("AML validation deadline must be finite")
    remaining = min(LIFECYCLE_SECONDS, deadline - time.time())
    if remaining <= CLEANUP_RESERVE_SECONDS:
        raise TimeoutError("Insufficient AML validation time remains after reserving cleanup")
    finish = asyncio.get_running_loop().time() + remaining
    return finish - CLEANUP_RESERVE_SECONDS, finish


async def assert_api_removed(resource_path, token, verify):
    async with asyncio.timeout(5 * 60):
        async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
            while True:
                response = await client.get(get_full_endpoint(f"/api{resource_path}"), headers=get_auth_header(token))
                if response.status_code == 404:
                    return
                if response.status_code != 200:
                    raise RuntimeError(f"Could not verify AML resource removal: HTTP {response.status_code}")
                await asyncio.sleep(10)


class AMLResources:
    def __init__(self, verify, work_finish, finish):
        self.verify = verify
        self.work_finish = work_finish
        self.finish = finish
        self.finalisers = []
        self.arm_resources = {}

    def own(self, name, callback, *args):
        self.finalisers.append((name, partial(callback, *args)))

    @asynccontextmanager
    async def creation(self):
        # Recovery of an accepted create gets a share of the reserve. The
        # remaining parents must still have time to start their own cleanup.
        reserve = self.finish - self.work_finish
        recovery_finish = self.work_finish + reserve / (len(self.finalisers) + 1)
        async with cleanup_deadline(recovery_finish - asyncio.get_running_loop().time()):
            async with asyncio.timeout(60 * 60):
                yield

    async def workspace(self):
        async with self.creation():
            resource_path, resource_id = await create_or_get_test_workspace(
                auth_type="Automatic", verify=self.verify, pre_created_workspace_id=""
            )
        self.own(resource_path, self.remove, resource_path, None)
        return resource_path, resource_id

    async def create(self, payload, endpoint, workspace_id):
        token = await get_workspace_owner_token(workspace_id, self.verify)
        async with self.creation():
            resource_path, resource_id = await post_resource(
                payload, endpoint, token, self.verify, cleanup_failed_create=True
            )
        self.own(resource_path, self.remove, resource_path, workspace_id)
        return resource_path, resource_id

    def track_arm(self, resource_path, arm, arm_id):
        self.arm_resources[resource_path] = (arm, arm_id)

    async def remove(self, resource_path, workspace_id):
        token = (
            await get_workspace_owner_token(workspace_id, self.verify)
            if workspace_id is not None
            else await get_admin_token(self.verify)
        )
        await disable_and_delete_resource(f"/api{resource_path}", token, self.verify, allow_failed_disable=True)
        await assert_api_removed(resource_path, token, self.verify)
        if resource_path in self.arm_resources:
            await assert_removed(*self.arm_resources[resource_path])

    async def close(self):
        failures = []
        while self.finalisers:
            seconds = (self.finish - asyncio.get_running_loop().time()) / len(self.finalisers)
            name, callback = self.finalisers.pop()
            try:
                async with cleanup_deadline(seconds):
                    await callback()
            except (Exception, asyncio.CancelledError) as error:
                error.add_note(f"AML validation cleanup failed for {name}")
                failures.append(error)
        return failures


@asynccontextmanager
async def aml_lifecycle(verify):
    work_finish, finish = lifecycle_deadlines()
    resources = AMLResources(verify, work_finish, finish)
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
            failure = original or cancelled
            if failure is not None:
                for error in failures:
                    failure.add_note(f"AML resource cleanup also failed: {error!r}; {error.__notes__}")
            elif failures:
                raise BaseExceptionGroup("AML resource cleanup failed", failures)
            if original is None and cancelled is not None:
                raise cancelled
