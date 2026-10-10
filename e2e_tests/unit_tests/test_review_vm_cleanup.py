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
