"""Check ownership when an Airlock review workspace is reused."""

import unittest
from unittest.mock import AsyncMock, patch

from e2e_tests import conftest as fixtures


class ReviewWorkspaceOwnershipTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.object(fixtures.config, "TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_ID", "existing"))
        self.enterContext(patch.object(fixtures.config, "TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_SERVICE_ID", ""))
        self.enterContext(
            patch.object(
                fixtures, "create_or_get_test_workspace", AsyncMock(return_value=("/workspaces/existing", "existing"))
            )
        )
        self.enterContext(patch.object(fixtures, "get_admin_token", AsyncMock(return_value="admin")))
        self.enterContext(patch.object(fixtures, "get_workspace_auth_details", AsyncMock(return_value=("owner", {}))))
        self.create_service = self.enterContext(
            patch.object(
                fixtures,
                "create_or_get_test_workpace_service",
                AsyncMock(return_value=("/workspaces/existing/workspace-services/new", "new")),
            )
        )
        self.delete_service = self.enterContext(patch.object(fixtures, "disable_and_delete_ws_resource", AsyncMock()))
        self.delete_workspace = self.enterContext(
            patch.object(fixtures, "disable_and_delete_tre_resource", AsyncMock())
        )

    def fixture(self):
        return fixtures.setup_test_airlock_import_review_workspace_and_guacamole_service.__wrapped__(None, True, None)

    async def finish(self, fixture):
        with self.assertRaises(StopAsyncIteration):
            await anext(fixture)

    async def test_created_child_is_removed_and_reused_parent_is_preserved(self):
        fixture = self.fixture()
        await anext(fixture)
        await self.finish(fixture)
        self.delete_service.assert_awaited_once_with("/workspaces/existing/workspace-services/new", "existing", True)
        self.delete_workspace.assert_not_awaited()

    async def test_reused_child_is_preserved(self):
        with patch.object(fixtures.config, "TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_SERVICE_ID", "existing-child"):
            fixture = self.fixture()
            await anext(fixture)
            await self.finish(fixture)
        self.delete_service.assert_not_awaited()
        self.delete_workspace.assert_not_awaited()

    async def test_owned_parent_uses_cascading_cleanup(self):
        with patch.object(fixtures.config, "TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_ID", ""):
            fixture = self.fixture()
            await anext(fixture)
            await self.finish(fixture)
        self.delete_service.assert_not_awaited()
        self.delete_workspace.assert_awaited_once_with("/workspaces/existing", True)

    async def test_failed_child_cleanup_still_calls_parent_cleanup(self):
        self.delete_service.side_effect = RuntimeError("child delete failed")
        with patch.object(fixtures, "clean_up_test_workspace", AsyncMock()) as parent:
            fixture = self.fixture()
            await anext(fixture)
            with self.assertRaisesRegex(RuntimeError, "child delete failed"):
                await anext(fixture)
            parent.assert_awaited_once()

    async def test_failed_child_setup_does_not_delete_reused_workspace(self):
        self.create_service.side_effect = RuntimeError("service setup failed")
        with self.assertRaisesRegex(RuntimeError, "service setup failed"):
            await anext(self.fixture())
        self.delete_service.assert_not_awaited()
        self.delete_workspace.assert_not_awaited()
