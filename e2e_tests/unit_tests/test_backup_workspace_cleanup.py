"""Exercise backup workspace cleanup through the real E2E test and API helpers."""

import json
import unittest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, MockTransport, Response

from e2e_tests import helpers
from e2e_tests import test_backups as backups
from e2e_tests.resources import resource, strings


class BackupWorkspaceCleanupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.object(helpers.config, "TRE_URL", "https://tre.example.test"))
        self.enterContext(patch.object(backups, "get_admin_token", new=AsyncMock(return_value="admin-token")))
        self.resource_path = "/workspaces/backup-workspace"
        self.requests = []

    def mock_api(
        self,
        *,
        enabled=True,
        install=strings.RESOURCE_STATUS_DEPLOYED,
        disable=strings.RESOURCE_STATUS_UPDATED,
        delete=strings.RESOURCE_STATUS_DELETED,
        post_status=202,
        missing_output=False,
    ):
        def handle(request):
            if request.url.path == "/api/workspace-templates/tre-workspace-base":
                return Response(200, json={"properties": {"enable_backup": {"type": "boolean"}}})
            self.requests.append(request)
            phase = request.url.path.rsplit("/", 1)[-1]
            response_status = 200
            if request.method == "POST":
                self.assertEqual(request.url.path, "/api/workspaces")
                properties = json.loads(request.content)["properties"]
                self.assertEqual(properties["enable_backup"], enabled)
                if enabled:
                    self.assertIs(properties["delete_backups_on_uninstall"], True)
                else:
                    self.assertNotIn("delete_backups_on_uninstall", properties)
                phase, response_status, state = "install", post_status, "deploying"
            elif request.method == "PATCH":
                self.assertEqual(request.url.path, f"/api{self.resource_path}")
                self.assertEqual(json.loads(request.content), {"isEnabled": False})
                phase, response_status, state = "disable", 202, "updating"
            elif request.method == "DELETE":
                self.assertEqual(request.url.path, f"/api{self.resource_path}")
                phase, state = "delete", "deleting"
            elif request.url.path == f"/api{self.resource_path}":
                properties = {
                    key: f"backup-{key}" if enabled else ""
                    for key in ["backup_vault_name", "vm_backup_policy_id", "fileshare_backup_policy_id"]
                }
                if missing_output:
                    properties.pop("fileshare_backup_policy_id")
                return Response(200, json={"workspace": {"deploymentStatus": "deployed", "properties": properties}})
            else:
                self.assertEqual(request.method, "GET")
                state = {"install": install, "disable": disable, "delete": delete}[phase]
                if isinstance(state, Exception):
                    raise state
            return Response(
                response_status,
                headers={"Location": f"/api/operations/{phase}"},
                json={
                    "operation": {
                        "resourcePath": self.resource_path,
                        "resourceId": "backup-workspace",
                        "status": state,
                        "message": "Mock operation outcome",
                        "steps": [],
                    }
                },
            )

        def create_client(**_):
            return AsyncClient(transport=MockTransport(handle))

        self.enterContext(patch.object(helpers, "AsyncClient", side_effect=create_client))
        self.enterContext(patch.object(resource, "AsyncClient", side_effect=create_client))

    def assert_deleted(self):
        self.assertEqual([r.method for r in self.requests[-4:]], ["PATCH", "GET", "DELETE", "GET"])
        self.assertEqual(self.requests[-2].url.path, f"/api{self.resource_path}")

    async def test_success_cleans_up_both_backup_settings(self):
        for enabled in [True, False]:
            with self.subTest(enabled=enabled):
                self.requests = []
                self.mock_api(enabled=enabled)
                await backups.test_create_base_workspace_with_backup_setting(enabled, enabled, True)
                self.assert_deleted()

    async def test_failed_deployment_cleans_up_even_if_disable_fails(self):
        self.mock_api(
            install=strings.RESOURCE_STATUS_DEPLOYMENT_FAILED, disable=strings.RESOURCE_STATUS_UPDATING_FAILED
        )
        with self.assertRaises(AssertionError):
            await backups.test_create_base_workspace_with_backup_setting(True, True, True)
        self.assert_deleted()
        self.assertEqual([r.method for r in self.requests], ["POST", "GET", "PATCH", "GET", "DELETE", "GET"])

    async def test_output_assertion_failure_still_cleans_up(self):
        self.mock_api(missing_output=True)
        with self.assertRaisesRegex(AssertionError, "fileshare_backup_policy_id"):
            await backups.test_create_base_workspace_with_backup_setting(True, True, True)
        self.assert_deleted()

    async def test_cleanup_failure_preserves_original_polling_error(self):
        failure = RuntimeError("backup registration polling failed")
        self.mock_api(install=failure, delete=strings.RESOURCE_STATUS_DELETING_FAILED)
        with self.assertRaises(RuntimeError) as caught:
            await backups.test_create_base_workspace_with_backup_setting(True, True, True)
        self.assertIs(caught.exception, failure)
        self.assertIn("Cleanup of /workspaces/backup-workspace also failed", caught.exception.__notes__[0])
        self.assert_deleted()

    async def test_cleanup_failure_fails_a_successful_deployment(self):
        self.mock_api(delete=strings.RESOURCE_STATUS_DELETING_FAILED)
        with self.assertRaises(AssertionError):
            await backups.test_create_base_workspace_with_backup_setting(True, True, True)
        self.assert_deleted()

    async def test_rejected_creation_does_not_attempt_cleanup(self):
        self.mock_api(post_status=403)
        with self.assertRaises(AssertionError):
            await backups.test_create_base_workspace_with_backup_setting(True, True, True)
        self.assertEqual([r.method for r in self.requests], ["POST"])


if __name__ == "__main__":
    unittest.main()
