"""Retain ownership of accepted resources across setup cancellation."""

import asyncio
from contextlib import asynccontextmanager
import json
import unittest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, MockTransport, Response

from e2e_tests import conftest as fixtures, helpers
from e2e_tests.resources import resource


@asynccontextmanager
async def template(*args):
    yield Response(200, json={"properties": {}})


class AcceptedResourceCleanupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requests = []
        self.path = "/workspaces/new-workspace"
        self.states = ["deploying", "deployed"]
        self.disable_status = 202
        self.create_status = 202
        self.block_delete = False
        self.poll_started = asyncio.Event()
        self.delete_started = asyncio.Event()
        self.release_delete = asyncio.Event()
        self.enterContext(patch.object(helpers.config, "TRE_URL", "https://tre.example.test"))
        self.enterContext(patch.object(fixtures, "get_admin_token", AsyncMock(return_value="admin-token")))
        self.enterContext(patch.object(fixtures, "get_template", template))
        self.enterContext(patch.object(fixtures.random, "uniform", return_value=0))
        self.enterContext(patch.object(fixtures, "post_resource", resource.post_resource))
        self.enterContext(
            patch.object(
                resource, "AsyncClient", side_effect=lambda **_: AsyncClient(transport=MockTransport(self.handle))
            )
        )

    async def handle(self, request):
        self.requests.append((request.method, request.url.path))
        code = 200
        phase = request.url.path.rsplit("/", 1)[-1]
        if request.method == "POST":
            phase, state, code = "install", "deploying", self.create_status
        elif request.method == "PATCH":
            self.assertEqual(json.loads(request.content), {"isEnabled": False})
            phase, state, code = "disable", "updating", self.disable_status
        elif request.method == "DELETE":
            self.delete_started.set()
            if self.block_delete:
                await self.release_delete.wait()
            phase, state = "delete", "deleting"
        elif phase == "install":
            self.poll_started.set()
            state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        else:
            state = {"disable": "updated", "delete": "deleted"}[phase]
        return Response(
            code,
            headers={"Location": f"/api/operations/{phase}"},
            json={
                "operation": {
                    "resourcePath": self.path,
                    "resourceId": self.path.rsplit("/", 1)[-1],
                    "status": state,
                    "message": "Mock operation",
                    "steps": [],
                }
            },
        )

    async def create(self, **kwargs):
        return await resource.post_resource({}, "/api/workspaces", "token", True, cleanup_failed_create=True, **kwargs)

    async def test_workspace_setup_timeout_removes_the_accepted_workspace(self):
        with self.assertRaises(TimeoutError):
            async with asyncio.timeout(0.01):
                await fixtures.create_or_get_test_workspace("Automatic", True)
        self.assertEqual(
            [method for method, _ in self.requests], ["POST", "GET", "GET", "PATCH", "GET", "DELETE", "GET"]
        )
        self.assertEqual(self.requests[-2], ("DELETE", "/api" + self.path))

    async def test_service_timeout_in_existing_workspace_deletes_only_the_new_service(self):
        self.path = "/workspaces/existing/workspace-services/new-service"
        with self.assertRaises(TimeoutError):
            async with asyncio.timeout(0.01):
                await fixtures.create_or_get_test_workpace_service("/workspaces/existing", "token", "", True)
        self.assertEqual([path for method, path in self.requests if method == "DELETE"], ["/api" + self.path])

    async def test_failed_deployment_still_cleans_up_and_preserves_failure(self):
        self.states = ["deployment_failed"]
        with self.assertRaises(AssertionError):
            await self.create()
        self.assertIn(("DELETE", "/api" + self.path), self.requests)

    async def test_rejected_creation_does_not_delete_anything(self):
        self.create_status = 403
        with self.assertRaises(AssertionError):
            await self.create()
        self.assertEqual(self.requests, [("POST", "/api/workspaces")])

    async def test_pending_deployment_recovery_has_its_own_bound_and_records_resource(self):
        self.states = ["deploying"]
        with patch.object(resource, "FAILED_CREATE_CLEANUP_TIMEOUT_SECONDS", 0.01):
            with self.assertRaises(TimeoutError) as caught:
                async with asyncio.timeout(0.01):
                    await self.create()
        self.assertNotIn("PATCH", [method for method, _ in self.requests])
        note = caught.exception.__cause__.__notes__[0]
        self.assertIn(self.path, note)
        self.assertIn("/api/operations/install", note)

    async def test_cleanup_failure_is_attached_to_the_original_timeout(self):
        self.disable_status = 403
        with self.assertRaises(TimeoutError) as caught:
            async with asyncio.timeout(0.01):
                await self.create()
        self.assertIn("also failed", caught.exception.__cause__.__notes__[0])
        self.assertNotIn("DELETE", [method for method, _ in self.requests])

    async def test_repeated_cancellation_waits_for_cleanup_to_finish(self):
        self.block_delete = True
        task = asyncio.create_task(self.create())
        await asyncio.wait_for(self.poll_started.wait(), 1)
        task.cancel()
        await asyncio.wait_for(self.delete_started.wait(), 1)
        task.cancel()
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        self.release_delete.set()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(task, 1)
        self.assertEqual(self.requests[-1], ("GET", "/api/operations/delete"))

    async def test_cleanup_option_rejects_updates_and_unpolled_creates(self):
        for options in ({"method": "PATCH"}, {"wait": False}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                await self.create(**options)
        self.assertEqual(self.requests, [])

    async def test_precreated_resources_are_returned_without_mutation(self):
        await fixtures.create_or_get_test_workspace("Automatic", True, pre_created_workspace_id="existing")
        await fixtures.create_or_get_test_workpace_service("/workspaces/existing", "token", "existing-service", True)
        self.assertEqual(self.requests, [])
