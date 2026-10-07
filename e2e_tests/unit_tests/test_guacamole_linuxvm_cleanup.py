"""Exercise Linux VM cleanup through the real polling and deletion helpers."""

import json
import unittest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, MockTransport, Response

from e2e_tests import helpers
from e2e_tests import test_guacamole_linuxvm as linuxvm
from e2e_tests.resources import resource, strings


class LinuxVmCleanupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.object(helpers.config, "TRE_URL", "https://tre.example.test"))
        self.enterContext(patch.object(linuxvm, "get_workspace_owner_token", new=AsyncMock(return_value="token")))
        self.fixture = ("/workspaces/ws", "ws", "/workspaces/ws/workspace-services/service", "service")
        self.resource_path = self.fixture[2] + "/user-resources/linux"
        self.requests = []

    def mock_api(
        self,
        outcome,
        *,
        post_status=202,
        disable_status=202,
        disable_outcome=strings.RESOURCE_STATUS_UPDATED,
        delete_outcome=strings.RESOURCE_STATUS_DELETED,
    ):
        def handle(request):
            self.requests.append(request)
            phase = request.url.path.rsplit("/", 1)[-1]
            response_status = 200
            if request.method == "POST":
                phase, response_status, state = "install", post_status, "deploying"
            elif request.method == "PATCH":
                self.assertEqual(json.loads(request.content), {"isEnabled": False})
                phase, response_status, state = "disable", disable_status, "updating"
            elif request.method == "DELETE":
                phase, state = "delete", "deleting"
            else:
                self.assertEqual(request.method, "GET")
                state = {"install": outcome, "disable": disable_outcome, "delete": delete_outcome}[phase]
                if isinstance(state, Exception):
                    raise state
            return Response(
                response_status,
                headers={"Location": f"/api/operations/{phase}"},
                json={
                    "operation": {
                        "resourcePath": self.resource_path,
                        "resourceId": "linux",
                        "status": state,
                        "message": "Mock deployment outcome",
                        "steps": [],
                    }
                },
            )

        def create_client(**_):
            return AsyncClient(transport=MockTransport(handle))

        self.enterContext(patch.object(linuxvm, "AsyncClient", side_effect=create_client))
        self.enterContext(patch.object(resource, "AsyncClient", side_effect=create_client))

    def assert_deleted(self):
        self.assertEqual(
            [request.method for request in self.requests], ["POST", "GET", "PATCH", "GET", "DELETE", "GET"]
        )
        self.assertEqual(self.requests[-2].url.path, f"/api{self.resource_path}")

    async def test_success_cleans_up_vm_in_reused_service(self):
        self.mock_api(strings.RESOURCE_STATUS_DEPLOYED)
        await linuxvm.test_create_guacamole_linux_vm(self.fixture, True)
        self.assert_deleted()

    async def test_failed_bootstrap_cleans_up_after_failed_disable(self):
        self.mock_api(
            strings.RESOURCE_STATUS_DEPLOYMENT_FAILED, disable_outcome=strings.RESOURCE_STATUS_UPDATING_FAILED
        )
        with self.assertRaises(AssertionError):
            await linuxvm.test_create_guacamole_linux_vm(self.fixture, True)
        self.assert_deleted()

    async def test_polling_error_still_cleans_up(self):
        # Use a non-retried error to verify cleanup without delaying the test.
        failure = RuntimeError("poll failed")
        self.mock_api(failure)
        with self.assertRaises(RuntimeError) as caught:
            await linuxvm.test_create_guacamole_linux_vm(self.fixture, True)
        self.assertIs(caught.exception, failure)
        self.assert_deleted()

    async def test_cleanup_failure_preserves_bootstrap_error(self):
        failure = RuntimeError("bootstrap failed")
        self.mock_api(failure, delete_outcome=strings.RESOURCE_STATUS_DELETING_FAILED)
        with self.assertRaises(RuntimeError) as caught:
            await linuxvm.test_create_guacamole_linux_vm(self.fixture, True)
        self.assertIs(caught.exception, failure)
        self.assertIn("Linux VM cleanup also failed", caught.exception.__notes__[0])
        self.assert_deleted()

    async def test_cleanup_failure_fails_a_successful_bootstrap(self):
        self.mock_api(strings.RESOURCE_STATUS_DEPLOYED, delete_outcome=strings.RESOURCE_STATUS_DELETING_FAILED)
        with self.assertRaises(AssertionError):
            await linuxvm.test_create_guacamole_linux_vm(self.fixture, True)
        self.assert_deleted()

    async def test_rejected_creation_does_not_delete_a_resource(self):
        self.mock_api("rejected", post_status=403)
        with self.assertRaises(AssertionError):
            await linuxvm.test_create_guacamole_linux_vm(self.fixture, True)
        self.assertEqual([request.method for request in self.requests], ["POST"])

    async def test_rejected_disable_does_not_delete(self):
        self.mock_api(strings.RESOURCE_STATUS_DEPLOYMENT_FAILED, disable_status=403)
        with self.assertRaises(AssertionError) as caught:
            await linuxvm.test_create_guacamole_linux_vm(self.fixture, True)
        self.assertIn("Linux VM cleanup also failed", caught.exception.__notes__[0])
        self.assertEqual([request.method for request in self.requests], ["POST", "GET", "PATCH"])

    async def test_successful_bootstrap_still_requires_successful_disable(self):
        self.mock_api(strings.RESOURCE_STATUS_DEPLOYED, disable_outcome=strings.RESOURCE_STATUS_UPDATING_FAILED)
        with self.assertRaises(AssertionError):
            await linuxvm.test_create_guacamole_linux_vm(self.fixture, True)
        self.assertEqual([request.method for request in self.requests], ["POST", "GET", "PATCH", "GET"])


if __name__ == "__main__":
    unittest.main()
