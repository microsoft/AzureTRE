"""Verify that the Linux provisioning test cleans up successful and failed VMs."""

import unittest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, MockTransport, Response

from e2e_tests import helpers
from e2e_tests import test_guacamole_linuxvm as linuxvm
from e2e_tests.resources import strings


class LinuxVmCleanupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.object(helpers.config, "TRE_URL", "https://tre.example.test"))
        self.enterContext(patch.object(linuxvm, "get_workspace_owner_token", new=AsyncMock(return_value="token")))
        self.cleanup = self.enterContext(patch.object(linuxvm, "disable_and_delete_ws_resource", new=AsyncMock()))
        self.fixture = ("/workspaces/ws", "ws", "/workspaces/ws/workspace-services/service", "service")
        self.resource_path = self.fixture[2] + "/user-resources/linux"
        self.requests = []

    def mock_api(self, outcome, post_status=202):
        def handle(request):
            self.requests.append(request)
            if request.method == "GET" and isinstance(outcome, Exception):
                raise outcome
            return Response(
                post_status if request.method == "POST" else 200,
                headers={"Location": "/api/operations/install-linux"},
                json={
                    "operation": {
                        "resourcePath": self.resource_path,
                        "status": "deploying" if request.method == "POST" else outcome,
                        "message": "Mock deployment outcome",
                        "steps": [],
                    }
                },
            )

        client = AsyncClient(transport=MockTransport(handle))
        self.enterContext(patch.object(linuxvm, "AsyncClient", return_value=client))

    async def test_success_cleans_up_vm_in_reused_service(self):
        self.mock_api(strings.RESOURCE_STATUS_DEPLOYED)
        await linuxvm.test_create_guacamole_linux_vm(self.fixture, True)
        self.cleanup.assert_awaited_once_with(self.resource_path, "ws", True)
        self.assertEqual([request.method for request in self.requests], ["POST", "GET"])

    async def test_failed_bootstrap_cleans_up_and_preserves_failure(self):
        self.mock_api(strings.RESOURCE_STATUS_DEPLOYMENT_FAILED)
        with self.assertRaises(AssertionError):
            await linuxvm.test_create_guacamole_linux_vm(self.fixture, True)
        self.cleanup.assert_awaited_once_with(self.resource_path, "ws", True)

    async def test_polling_error_still_cleans_up(self):
        # Use a non-retried error to verify the finalizer without delaying the test.
        self.mock_api(RuntimeError("poll failed"))
        with self.assertRaisesRegex(RuntimeError, "poll failed"):
            await linuxvm.test_create_guacamole_linux_vm(self.fixture, True)
        self.cleanup.assert_awaited_once_with(self.resource_path, "ws", True)

    async def test_rejected_creation_does_not_delete_a_resource(self):
        self.mock_api("rejected", post_status=403)
        with self.assertRaises(AssertionError):
            await linuxvm.test_create_guacamole_linux_vm(self.fixture, True)
        self.cleanup.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
