"""Exercise the accepted-disable boundary under the real fixture deadline."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, MockTransport, Response
from e2e_tests import conftest as fixtures, helpers
from e2e_tests.resources import resource


class DisableDeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def run_cleanup(self, stall):
        self.requests = []

        async def handle(request):
            self.requests.append((request.method, request.url.path))
            if request.method == "PATCH":
                phase, state, code = "disable", "updating", 202
            elif request.method == "DELETE":
                phase, state, code = "delete", "deleting", 200
            else:
                phase, code = request.url.path.rsplit("/", 1)[-1], 200
                if phase == "disable":
                    await asyncio.sleep(1 if stall else 0.001)
                state = {"disable": "updated", "delete": "deleted"}[phase]
            return Response(
                code,
                headers={"Location": f"/api/operations/{phase}"},
                json={
                    "operation": {
                        "resourceId": "owned-workspace",
                        "status": state,
                        "message": "test",
                        "steps": [],
                    }
                },
            )

        with (
            patch.object(helpers.config, "TRE_URL", "https://tre.example.test"),
            patch.object(resource, "AsyncClient", side_effect=lambda **_: AsyncClient(transport=MockTransport(handle))),
            patch.object(fixtures, "disable_and_delete_resource", resource.disable_and_delete_resource),
            patch.object(fixtures, "get_admin_token", AsyncMock(return_value="token")),
            patch.object(fixtures, "CLEANUP_TIMEOUT_SECONDS", 0.03),
        ):
            await fixtures.clean_up_test_workspace("", "/workspaces/owned-workspace", True)

    async def test_accepted_disable_reaches_terminal_state_before_delete(self):
        await self.run_cleanup(False)
        self.assertEqual([method for method, _ in self.requests], ["PATCH", "GET", "DELETE", "GET"])

    async def test_stalled_disable_has_bounded_failure_and_does_not_send_conflicting_delete(self):
        with self.assertLogs(resource.LOGGER, level="ERROR") as logs:
            with self.assertRaisesRegex(TimeoutError, "Cleanup of /workspaces/owned-workspace exceeded"):
                await asyncio.wait_for(self.run_cleanup(True), 0.5)
        self.assertEqual([method for method, _ in self.requests], ["PATCH", "GET"])
        self.assertIn("/api/operations/disable", "\n".join(logs.output))
        await asyncio.sleep(0.01)
        self.assertEqual([method for method, _ in self.requests], ["PATCH", "GET"])
