"""Exercise the owned base-workspace case through real HTTP helpers without Azure."""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, MockTransport, Response

import helpers as short_helpers
from resources import resource as short_resource
from e2e_tests import conftest as fixtures, helpers, test_workspace_base as base
from e2e_tests.resources import resource, workspace


WORKSPACE = "11111111-1111-4111-8111-111111111111"
OPERATIONS = {
    phase: f"00000000-0000-4000-8000-00000000000{index}"
    for index, phase in enumerate(("install", "disable", "delete"), 1)
}


class BaseWorkspaceLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.path = f"/workspaces/{WORKSPACE}"
        self.requests = []
        self.deleted = False
        self.enterContext(patch.object(helpers.config, "TRE_URL", "https://tre.example.test"))
        self.enterContext(patch.object(helpers.config, "TEST_WORKSPACE_ID", "existing-unrelated-workspace"))
        self.enterContext(patch.object(fixtures, "get_admin_token", AsyncMock(return_value="admin-token")))
        self.enterContext(patch.object(base, "get_admin_token", AsyncMock(return_value="admin-token")))
        self.enterContext(patch.object(fixtures.asyncio, "sleep", AsyncMock()))
        self.enterContext(patch.object(workspace, "get_token", return_value="workspace-token"))
        self.enterContext(
            patch(
                "httpx.AsyncHTTPTransport.handle_async_request",
                AsyncMock(side_effect=AssertionError("Unexpected live HTTP request in an offline test")),
            )
        )

    def mock_api(
        self,
        *,
        denied=False,
        missing_scope=False,
        retained=False,
        delete_failed=False,
        install_failed=False,
        rejected=False,
        block_services=False,
    ):
        self.service_started = asyncio.Event()

        async def handle(request):
            self.requests.append(request)
            uri = request.url.path
            if uri == "/api/workspace-templates/tre-workspace-base":
                return Response(200, json={"properties": {"enable_backup": {"type": "boolean"}}})
            if request.method == "POST":
                self.assertEqual(uri, "/api/workspaces")
                payload = json.loads(request.content)
                self.assertEqual(payload["templateName"], "tre-workspace-base")
                self.assertEqual(payload["properties"]["auth_type"], "Automatic")
                self.assertIs(payload["properties"]["enable_backup"], False)
                phase, code, state = "install", 400 if rejected else 202, "deploying"
            elif request.method == "PATCH":
                self.assertEqual(uri, "/api" + self.path)
                self.assertEqual(json.loads(request.content), {"isEnabled": False})
                phase, code, state = "disable", 202, "updating"
            elif request.method == "DELETE":
                self.assertEqual(uri, "/api" + self.path)
                phase, code, state = "delete", 200, "deleting"
            elif uri.endswith("/workspace-services"):
                self.assertEqual(request.headers["authorization"], "Bearer workspace-token")
                self.service_started.set()
                if block_services:
                    await asyncio.Event().wait()
                return Response(403 if denied else 200, json={"workspaceServices": []})
            elif uri == "/api" + self.path:
                self.assertEqual(request.headers["authorization"], "Bearer admin-token")
                if self.deleted and not retained:
                    return Response(404)
                return Response(
                    200,
                    json={
                        "workspace": {
                            "id": WORKSPACE,
                            "templateName": "tre-workspace-base",
                            "deploymentStatus": "deployed",
                            "isEnabled": True,
                            "properties": {} if missing_scope else {"scope_id": "workspace-scope"},
                        }
                    },
                )
            else:
                phase = next(name for name, value in OPERATIONS.items() if uri.endswith(value))
                code = 200
                state = {
                    "install": "deployment_failed" if install_failed else "deployed",
                    "disable": "updated",
                    "delete": "deleting_failed" if delete_failed else "deleted",
                }[phase]
                if state == "deleted":
                    self.deleted = True
            return Response(
                code,
                headers={"Location": f"/api{self.path}/operations/{OPERATIONS[phase]}"},
                json={
                    "operation": {
                        "resourcePath": self.path,
                        "resourceId": WORKSPACE,
                        "status": state,
                        "message": "Mock result",
                        "steps": [],
                    },
                },
            )

        def client(**_):
            return AsyncClient(transport=MockTransport(handle))

        for module in (base, workspace, resource, short_resource, short_helpers):
            self.enterContext(patch.object(module, "AsyncClient", side_effect=client))

    def assert_owned_workspace_removed(self):
        self.assertTrue(self.deleted)
        self.assertEqual([str(r.url.path) for r in self.requests if r.method == "DELETE"], ["/api" + self.path])
        self.assertFalse(any("existing-unrelated-workspace" in str(r.url) for r in self.requests))

    async def test_creates_owned_workspace_uses_workspace_token_and_checks_removal(self):
        self.mock_api()
        await base.test_base_workspace_lifecycle(True)
        self.assert_owned_workspace_removed()
        self.assertEqual(self.requests[-1].url.path, "/api" + self.path)

    async def test_failed_access_check_still_removes_the_workspace(self):
        self.mock_api(denied=True)
        with self.assertRaisesRegex(AssertionError, "cannot list services"):
            await base.test_base_workspace_lifecycle(True)
        self.assert_owned_workspace_removed()

    async def test_missing_workspace_scope_still_removes_the_workspace(self):
        self.mock_api(missing_scope=True)
        with self.assertRaisesRegex(Exception, "Scope Id not found"):
            await base.test_base_workspace_lifecycle(True)
        self.assert_owned_workspace_removed()

    async def test_visible_workspace_after_successful_delete_fails(self):
        self.mock_api(retained=True)
        with self.assertRaisesRegex(AssertionError, "remains visible after uninstall"):
            await base.test_base_workspace_lifecycle(True)

    async def test_cleanup_failure_preserves_the_original_assertion(self):
        self.mock_api(denied=True, delete_failed=True)
        with self.assertRaisesRegex(AssertionError, "cannot list services") as caught:
            await base.test_base_workspace_lifecycle(True)
        self.assertIn("Workspace cleanup also failed", "\n".join(caught.exception.__notes__))

    async def test_failed_accepted_install_is_removed_by_the_existing_recovery_helper(self):
        self.mock_api(install_failed=True)
        with self.assertRaises(AssertionError):
            await base.test_base_workspace_lifecycle(True)
        self.assert_owned_workspace_removed()

    async def test_rejected_creation_does_not_delete_any_workspace(self):
        self.mock_api(rejected=True)
        with self.assertRaises(AssertionError):
            await base.test_base_workspace_lifecycle(True)
        self.assertFalse(any(r.method == "DELETE" for r in self.requests))

    async def test_body_timeout_finishes_cleanup(self):
        self.mock_api(block_services=True)
        with patch.object(base, "BODY_TIMEOUT_SECONDS", 0.05):
            with self.assertRaises(TimeoutError):
                await base.test_base_workspace_lifecycle(True)
        self.assert_owned_workspace_removed()

    async def test_cancellation_during_access_check_finishes_cleanup(self):
        self.mock_api(block_services=True)
        task = asyncio.create_task(base.test_base_workspace_lifecycle(True))
        await asyncio.wait_for(self.service_started.wait(), 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(task, 1)
        self.assert_owned_workspace_removed()
