"""Reserve cleanup time for all resources created by the SQL validation case."""

import asyncio
from builtins import ExceptionGroup
from contextlib import asynccontextmanager
from functools import partial
import logging
import math
import os
import time

from e2e_tests import config
from e2e_tests.conftest import (
    clean_up_test_workspace,
    clean_up_test_workspace_service,
    create_or_get_test_workspace,
    create_or_get_test_workpace_service,
    get_workspace_owner_token,
)
from e2e_tests.resources.resource import disable_and_delete_resource, get_resource, post_resource
from e2e_tests.timeouts import cleanup_deadline

LOGGER = logging.getLogger(__name__)
LIFECYCLE_SECONDS = 270 * 60
CLEANUP_RESERVE_SECONDS = 120 * 60
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


def lifecycle_deadlines():
    """Use the job's absolute deadline, including time spent starting the container."""
    loop = asyncio.get_running_loop()
    configured = os.environ.get("SQL_VALIDATION_DEADLINE", "")
    deadline = float(configured) if configured else time.time() + LIFECYCLE_SECONDS
    if not math.isfinite(deadline):
        raise ValueError("SQL validation deadline must be finite")
    remaining = min(LIFECYCLE_SECONDS, deadline - time.time())
    if not 0 < remaining <= LIFECYCLE_SECONDS or remaining <= CLEANUP_RESERVE_SECONDS:
        raise TimeoutError("Insufficient SQL validation time remains after reserving cleanup")
    finish = loop.time() + remaining
    return finish - CLEANUP_RESERVE_SECONDS, finish


class SQLResources:
    def __init__(self, verify, finish):
        self.verify = verify
        self.finish = finish
        self.finalisers = []

    def own(self, name, callback, *args, **kwargs):
        self.finalisers.append((name, partial(callback, *args, **kwargs)))

    async def setup(self):
        # Keep these resources inside the SQL budget rather than session fixtures.
        workspace_path, workspace_id = await create_or_get_test_workspace(
            auth_type="Manual" if config.TEST_WORKSPACE_APP_ID else "Automatic",
            verify=self.verify,
            pre_created_workspace_id=config.TEST_WORKSPACE_ID,
            client_id=config.TEST_WORKSPACE_APP_ID,
            client_secret=config.TEST_WORKSPACE_APP_SECRET,
        )
        if not config.TEST_WORKSPACE_ID:
            self.own(workspace_path, clean_up_test_workspace, "", workspace_path, self.verify)
        token = await get_workspace_owner_token(workspace_id, self.verify)
        guacamole_path, guacamole_id = await create_or_get_test_workpace_service(
            workspace_path, token, config.TEST_WORKSPACE_SERVICE_ID, self.verify
        )
        if not config.TEST_WORKSPACE_SERVICE_ID:
            self.own(guacamole_path, clean_up_test_workspace_service, "", guacamole_path, workspace_id, self.verify)
        return workspace_path, workspace_id, guacamole_path, guacamole_id

    async def create(self, payload, endpoint, token):
        async with asyncio.timeout(60 * 60):
            resource_path, resource_id = await post_resource(
                payload, endpoint, token, self.verify, cleanup_failed_create=True
            )
        self.own(resource_path, self.delete, resource_path, token)
        return resource_path, resource_id

    async def delete(self, resource_path, token):
        while True:
            operations = (await get_resource(f"/api{resource_path}/operations", token, self.verify))["operations"]
            if all(op["status"] in TERMINAL_STATES for op in operations):
                break
            await asyncio.sleep(30)
        await disable_and_delete_resource(f"/api{resource_path}", token, self.verify, allow_failed_disable=True)

    async def close(self):
        failures = []
        while self.finalisers:
            # Each remaining resource gets a share. One slow delete must not use
            # the entire reserve before parent cleanup can even start.
            seconds = (self.finish - asyncio.get_running_loop().time()) / len(self.finalisers)
            name, callback = self.finalisers.pop()
            try:
                async with cleanup_deadline(seconds):
                    await callback()
            except Exception as error:
                error.add_note(f"SQL validation cleanup failed for {name}")
                LOGGER.error("SQL validation cleanup failed for %s: %r", name, error)
                failures.append(error)
        return failures


@asynccontextmanager
async def sql_lifecycle(verify):
    work_finish, finish = lifecycle_deadlines()
    resources = SQLResources(verify, finish)
    original = None
    # Accepted-create recovery inherits the same absolute limit. It cannot add
    # another hour after the lifecycle deadline.
    async with cleanup_deadline(finish - asyncio.get_running_loop().time()):
        try:
            async with asyncio.timeout_at(work_finish):
                yield resources
        except BaseException as error:
            original = error
            raise
        finally:
            # Repeated caller cancellation must wait for bounded recovery.
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
                    failure.add_note(f"SQL resource cleanup also failed: {error!r}; {error.__notes__}")
            elif failures:
                raise ExceptionGroup("SQL resource cleanup failed", failures)
            if original is None and cancelled is not None:
                raise cancelled
