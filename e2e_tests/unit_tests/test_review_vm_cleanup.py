"""Exercise review VM ownership after creation and during asynchronous deletion."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, MockTransport, Response
from e2e_tests import helpers, test_airlock as airlock
from e2e_tests.resources import resource


class ReviewVmCleanupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requests = []
        self.state = "deployed"
        self.active_operation = False
        self.path = "/workspaces/review/workspace-services/guac/user-resources/vm"
        self.enterContext(patch.object(helpers.config, "TRE_URL", "https://tre.example.test"))
        self.enterContext(patch.object(airlock, "post_resource", AsyncMock(return_value=(self.path, "vm"))))
        self.enterContext(
            patch.object(airlock, "delete_owned_resource_if_present", resource.delete_owned_resource_if_present)
        )
        self.enterContext(
            patch.object(
                resource, "AsyncClient", side_effect=lambda **_: AsyncClient(transport=MockTransport(self.handle))
            )
        )

    async def handle(self, request):
        self.requests.append((request.method, request.url.path))
        self.assertEqual(request.headers["Authorization"], "Bearer review-token")
        if request.method == "GET" and request.url.path == f"/api{self.path}":
            if self.state == "absent":
                return Response(404)
            return Response(200, json={"userResource": {"deploymentStatus": self.state}})
        if request.url.path.endswith("/operations"):
            return Response(200, json={"operations": [{"status": "deleting" if self.active_operation else "deployed"}]})
        if request.method == "PATCH":
            phase, code, state = "disable", 202, "updating"
        elif request.method == "DELETE":
            phase, code, state = "delete", 200, "deleting"
        else:
            phase, code = request.url.path.rsplit("/", 1)[-1], 200
            state = {"disable": "updated", "delete": "deleted"}[phase]
        return Response(
            code,
            headers={"Location": f"/api/operations/{phase}"},
            json={
                "operation": {
                    "resourceId": "vm",
                    "status": state,
                    "message": "test",
                    "steps": [],
                }
            },
        )

    def owner(self):
        return airlock.managed_review_vm("/workspaces/research", "request", "research-token", "review-token", True)

    async def test_successful_creation_is_cleaned_after_approval_failure(self):
        error = RuntimeError("approval failed")
        approve = AsyncMock(side_effect=error)
        with self.assertRaises(RuntimeError) as caught:
            async with self.owner() as owned:
                self.assertEqual(owned, self.path)
                await approve()
        self.assertIs(caught.exception, error)
        self.assertIn(("DELETE", f"/api{self.path}"), self.requests)

    async def test_body_cancellation_waits_for_child_cleanup(self):
        with self.assertRaises(TimeoutError):
            async with asyncio.timeout(0.01):
                async with self.owner():
                    await asyncio.sleep(1)
        self.assertEqual(self.requests[-1], ("GET", "/api/operations/delete"))

    async def test_normal_airlock_deletion_does_not_send_a_second_delete(self):
        self.state = "absent"
        async with self.owner():
            pass
        self.assertEqual(self.requests, [("GET", f"/api{self.path}")])

    async def test_active_approval_deletion_finishes_before_cleanup_returns(self):
        self.state, self.active_operation = "updating", True

        async def finish_operation(seconds):
            self.assertFalse(any(method in ("PATCH", "DELETE") for method, _ in self.requests))
            self.state = "absent"

        with patch.object(resource.asyncio, "sleep", finish_operation):
            async with self.owner():
                pass
        self.assertEqual([method for method, _ in self.requests], ["GET", "GET", "GET"])

    async def test_cleanup_failure_preserves_the_original_body_failure(self):
        original = RuntimeError("approval failed")
        approve = AsyncMock(side_effect=original)
        with patch.object(airlock, "delete_owned_resource_if_present", AsyncMock(side_effect=TimeoutError("stalled"))):
            with self.assertRaises(RuntimeError) as caught:
                async with self.owner():
                    await approve()
        self.assertIs(caught.exception, original)
        self.assertIn(self.path, str(caught.exception.__notes__))

    async def test_outer_timeout_during_recovery_preserves_body_failure(self):
        started, finished = asyncio.Event(), asyncio.Event()
        original = TimeoutError("automatic deletion stalled")

        async def cleanup(*args):
            started.set()
            await asyncio.sleep(0.03)
            finished.set()

        @airlock.async_test_timeout(0.01)
        async def run():
            async with self.owner():
                raise original

        with patch.object(airlock, "delete_owned_resource_if_present", cleanup):
            with self.assertRaises(TimeoutError) as caught:
                await run()
        self.assertTrue(started.is_set())
        self.assertTrue(finished.is_set())
        self.assertIs(caught.exception, original)

    async def test_repeated_cancellation_during_successful_exit_waits_for_cleanup(self):
        started, release, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def cleanup(*args):
            started.set()
            await release.wait()
            finished.set()

        async def run():
            async with self.owner():
                pass

        with patch.object(airlock, "delete_owned_resource_if_present", cleanup):
            task = asyncio.create_task(run())
            try:
                await asyncio.wait_for(started.wait(), 1)
                for _ in range(2):
                    task.cancel()
                    await asyncio.sleep(0)
                    self.assertFalse(task.done())
                release.set()
                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(task, 1)
                self.assertTrue(finished.is_set())
            finally:
                release.set()
                await asyncio.gather(task, return_exceptions=True)

    async def test_cleanup_deadline_after_outer_timeout_preserves_body_failure(self):
        original = RuntimeError("approval failed")
        stopped = asyncio.Event()

        async def cleanup(*args):
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()

        @airlock.async_test_timeout(0.01)
        async def run():
            async with self.owner():
                raise original

        with (
            patch.object(airlock, "delete_owned_resource_if_present", cleanup),
            patch.object(airlock, "cleanup_deadline", side_effect=lambda _: resource.cleanup_deadline(0.03)),
        ):
            with self.assertRaises(RuntimeError) as caught:
                await run()
        self.assertIs(caught.exception, original)
        self.assertTrue(stopped.is_set())
        self.assertIn("TimeoutError", str(original.__notes__))

    async def test_cleanup_deadline_failure_is_reported_after_successful_body(self):
        with (
            patch.object(airlock, "delete_owned_resource_if_present", AsyncMock(side_effect=TimeoutError("stalled"))),
            self.assertRaisesRegex(TimeoutError, "stalled"),
        ):
            async with self.owner():
                pass

    async def test_cancelled_recovery_preserves_the_original_failure(self):
        original = RuntimeError("approval failed")
        with patch.object(airlock, "delete_owned_resource_if_present", AsyncMock(side_effect=asyncio.CancelledError)):
            with self.assertRaises(RuntimeError) as caught:
                async with self.owner():
                    raise original
        self.assertIs(caught.exception, original)
        self.assertIn("CancelledError", str(original.__notes__))


class ReviewVmDeletionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.object(helpers.config, "TRE_URL", "https://tre.example.test"))
        self.requests = []

    async def run_states(self, states, **kwargs):
        remaining = iter(states)

        def respond(request):
            self.requests.append(request.method)
            self.assertEqual(request.headers["Authorization"], "Bearer review-token")
            state = next(remaining)
            if isinstance(state, int):
                return Response(state)
            return Response(200, json={"userResource": {"deploymentStatus": state}})

        with (
            patch.object(airlock, "AsyncClient", side_effect=lambda **_: AsyncClient(transport=MockTransport(respond))),
            patch.object(airlock.asyncio, "sleep", AsyncMock()),
        ):
            await airlock.wait_for_review_vm_deletion(
                "/workspaces/review/user-resources/vm", "review-token", True, **kwargs
            )

    async def test_fast_deletion_does_not_require_observing_updating(self):
        for states in ([404], ["awaiting_deletion", "deleting", 404], ["deleted"]):
            with self.subTest(states=states):
                self.requests.clear()
                await self.run_states(states)
                self.assertEqual(self.requests, ["GET"] * len(states))

    async def test_waits_through_disable_and_delete_progress(self):
        states = ["deployed", "awaiting_update", "updating", "updated", "awaiting_deletion", "deleting", 404]
        await self.run_states(states)
        self.assertEqual(len(self.requests), len(states))

    async def test_failed_deletion_is_not_reported_as_success(self):
        for state in ("updating_failed", "deleting_failed", "pipeline_failed"):
            with self.subTest(state=state):
                with self.assertRaisesRegex(AssertionError, state):
                    await self.run_states([state])

    async def test_server_error_is_not_treated_as_deleted(self):
        with self.assertRaises(AssertionError):
            await self.run_states([500])

    async def test_stalled_deletion_has_a_finite_deadline(self):
        def respond(request):
            return Response(200, json={"userResource": {"deploymentStatus": "deleting"}})

        with patch.object(
            airlock, "AsyncClient", side_effect=lambda **_: AsyncClient(transport=MockTransport(respond))
        ):
            with self.assertRaisesRegex(TimeoutError, "Last state: deleting"):
                await airlock.wait_for_review_vm_deletion("/vm", "review-token", True, timeout_seconds=0.01)
