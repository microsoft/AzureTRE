"""Exercise SQL setup, cancellation and nested cleanup with scaled deadlines."""

import asyncio
from builtins import ExceptionGroup
import os
import time
import traceback
import unittest
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

from e2e_tests.resources import sql_lifecycle as lifecycle
from e2e_tests.resources import resource
from httpx import AsyncClient, MockTransport, Response
from e2e_tests import helpers


class SQLDeadlineTests(unittest.IsolatedAsyncioTestCase):
    def budgets(self, *, total=0.5, reserve=0.4):
        patches = ExitStack()
        patches.enter_context(patch.object(lifecycle, "LIFECYCLE_SECONDS", total))
        patches.enter_context(patch.object(lifecycle, "CLEANUP_RESERVE_SECONDS", reserve))
        patches.enter_context(patch.dict(os.environ, SQL_VALIDATION_DEADLINE=""))
        return patches

    async def test_slow_body_reserves_cleanup_for_all_four_owned_resources(self):
        events = []

        async def delete(name):
            events.append(name + " start")
            await asyncio.sleep(0.03)
            events.append(name + " done")

        with self.budgets():
            with self.assertRaises(TimeoutError):
                async with lifecycle.sql_lifecycle(True) as owned:
                    for name in ("workspace", "guacamole", "sql", "vm"):
                        owned.own(name, delete, name)
                    await asyncio.sleep(10)
        self.assertEqual(
            events,
            [f"{name} {state}" for name in ("vm", "sql", "guacamole", "workspace") for state in ("start", "done")],
        )

    async def test_slow_delete_leaves_time_for_each_parent_and_reports_original_failure(self):
        events = []

        async def delete(name):
            events.append(name)
            if name == "vm":
                await asyncio.sleep(10)

        with self.budgets(total=0.2, reserve=0.15):
            with self.assertRaisesRegex(RuntimeError, "body failed") as caught:
                async with lifecycle.sql_lifecycle(True) as owned:
                    for name in ("workspace", "guacamole", "sql", "vm"):
                        owned.own(name, delete, name)
                    raise RuntimeError("body failed")
        self.assertEqual(events, ["vm", "sql", "guacamole", "workspace"])
        self.assertIn("TimeoutError", " ".join(caught.exception.__notes__))
        self.assertIn("vm", " ".join(caught.exception.__notes__))

    async def test_repeated_cancellation_waits_for_cleanup(self):
        started = asyncio.Event()
        finished = asyncio.Event()

        async def delete():
            started.set()
            await asyncio.sleep(0.06)
            finished.set()

        async def run():
            async with lifecycle.sql_lifecycle(True) as owned:
                owned.own("vm", delete)

        with self.budgets():
            task = asyncio.create_task(run())
            await started.wait()
            task.cancel()
            await asyncio.sleep(0.01)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(finished.is_set())

    async def test_setup_uses_work_deadline_and_removes_created_workspace(self):
        deleted = AsyncMock()
        setup_started = asyncio.Event()

        async def create_service(*args):
            setup_started.set()
            await asyncio.sleep(10)

        with (
            self.budgets(),
            patch.object(lifecycle.config, "TEST_WORKSPACE_ID", ""),
            patch.object(lifecycle.config, "TEST_WORKSPACE_SERVICE_ID", ""),
            patch.object(lifecycle, "create_or_get_test_workspace", AsyncMock(return_value=("/workspaces/ws", "ws"))),
            patch.object(lifecycle, "get_workspace_owner_token", AsyncMock(return_value="token")),
            patch.object(lifecycle, "create_or_get_test_workpace_service", create_service),
            patch.object(lifecycle, "clean_up_test_workspace", deleted),
        ):
            with self.assertRaises(TimeoutError):
                async with lifecycle.sql_lifecycle(True) as owned:
                    await owned.setup()
        self.assertTrue(setup_started.is_set())
        deleted.assert_awaited_once_with("", "/workspaces/ws", True)

    async def test_existing_workspace_and_service_are_not_owned(self):
        with (
            self.budgets(),
            patch.object(lifecycle.config, "TEST_WORKSPACE_ID", "existing"),
            patch.object(lifecycle.config, "TEST_WORKSPACE_SERVICE_ID", "existing-service"),
            patch.object(lifecycle, "create_or_get_test_workspace", AsyncMock(return_value=("/workspaces/ws", "ws"))),
            patch.object(lifecycle, "get_workspace_owner_token", AsyncMock(return_value="token")),
            patch.object(
                lifecycle, "create_or_get_test_workpace_service", AsyncMock(return_value=("/service", "service"))
            ),
        ):
            async with lifecycle.sql_lifecycle(True) as owned:
                await owned.setup()
                self.assertEqual(owned.finalisers, [])

    async def test_job_start_deadline_reduces_work_time(self):
        with patch.dict(os.environ, SQL_VALIDATION_DEADLINE=str(time.time() + 125 * 60)):
            work, finish = lifecycle.lifecycle_deadlines()
        self.assertAlmostEqual(work - asyncio.get_running_loop().time(), 5 * 60, delta=1)
        self.assertAlmostEqual(finish - work, 120 * 60, delta=1)

    async def test_job_start_deadline_refuses_late_start_before_creating_resources(self):
        for value in (str(time.time() + 60), str(time.time() - 1), "nan", "inf", "invalid"):
            with self.subTest(value=value), patch.dict(os.environ, SQL_VALIDATION_DEADLINE=value):
                with self.assertRaises((ValueError, TimeoutError)):
                    async with lifecycle.sql_lifecycle(True):
                        self.fail("A late or invalid job deadline must not start resource creation")

    async def test_failed_accepted_create_finishes_recovery_before_parent_cleanup(self):
        events = []
        states = iter(("deploying", "deployed"))
        child = "/workspaces/ws/workspace-services/sql"

        async def handle(request):
            phase = request.url.path.rsplit("/", 1)[-1]
            state, code = "deployed", 200
            if request.method == "POST":
                phase, state, code = "install", "deploying", 202
            elif request.method == "PATCH":
                phase, state, code = "disable", "updating", 202
            elif request.method == "DELETE":
                events.append("child delete start")
                await asyncio.sleep(0.03)
                events.append("child delete done")
                phase, state = "delete", "deleting"
            elif phase == "install":
                state = next(states)
            else:
                state = {"disable": "updated", "delete": "deleted"}[phase]
            return Response(
                code,
                headers={"Location": f"/api/operations/{phase}"},
                json={
                    "operation": {
                        "resourcePath": child,
                        "resourceId": "sql",
                        "status": state,
                        "message": "operation",
                        "steps": [],
                    }
                },
            )

        async def parent():
            events.append("parent delete")

        with (
            self.budgets(),
            patch.object(helpers.config, "TRE_URL", "https://tre.example.test"),
            patch.object(resource, "AsyncClient", side_effect=lambda **_: AsyncClient(transport=MockTransport(handle))),
        ):
            with self.assertRaises(TimeoutError):
                async with lifecycle.sql_lifecycle(True) as owned:
                    owned.own("workspace", parent)
                    await owned.create({}, "/api/workspaces/ws/workspace-services", "token")
        self.assertEqual(events, ["child delete start", "child delete done", "parent delete"])

    async def test_cleanup_failure_after_success_fails_the_case(self):
        with self.budgets():
            with self.assertRaises(ExceptionGroup) as caught:
                async with lifecycle.sql_lifecycle(True) as owned:
                    owned.own("vm", AsyncMock(side_effect=RuntimeError("DELETE_FAILED")))
        self.assertIn("DELETE_FAILED", str(caught.exception.exceptions[0]))

    async def test_absolute_deadline_bounds_failed_create_recovery(self):
        path = "/workspaces/ws/workspace-services/sql"
        parent = AsyncMock()

        async def handle(request):
            return Response(
                202 if request.method == "POST" else 200,
                headers={"Location": "/api/operations/install"},
                json={
                    "operation": {
                        "resourcePath": path,
                        "resourceId": "sql",
                        "status": "deploying",
                        "message": "operation",
                        "steps": [],
                    }
                },
            )

        started = asyncio.get_running_loop().time()
        with (
            self.budgets(total=0.15, reserve=0.1),
            patch.object(helpers.config, "TRE_URL", "https://tre.example.test"),
            patch.object(resource, "AsyncClient", side_effect=lambda **_: AsyncClient(transport=MockTransport(handle))),
        ):
            with self.assertRaises(TimeoutError) as caught:
                async with lifecycle.sql_lifecycle(True) as owned:
                    owned.own("workspace", parent)
                    await owned.create({}, "/api/workspaces/ws/workspace-services", "token")
        self.assertLess(asyncio.get_running_loop().time() - started, 1)
        # Expiry is explicit. No late cleanup task can outlive the SQL case.
        parent.assert_not_awaited()
        details = "".join(traceback.format_exception(caught.exception))
        self.assertIn("SQL validation cleanup failed for workspace", details)
        self.assertIn(path, details)
        self.assertEqual([task for task in asyncio.all_tasks() if task is not asyncio.current_task()], [])
