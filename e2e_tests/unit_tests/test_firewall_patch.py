"""Check firewall mutation, restoration and concurrent-change protection."""

import asyncio
from copy import deepcopy
import unittest
from unittest.mock import AsyncMock, patch

from e2e_tests import test_shared_services as shared


class FirewallPatchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original = {
            "display_name": "Core firewall",
            "rule_collections": [{"name": "original-rule"}],
            "private_ip": "10.0.0.1",
        }
        self.firewall = {"id": "firewall-id", "_etag": "original-etag", "properties": deepcopy(self.original)}
        self.enterContext(patch.object(shared, "get_admin_token", AsyncMock(return_value="token")))
        self.find = self.enterContext(
            patch.object(shared, "get_shared_service_by_name", AsyncMock(return_value=self.firewall))
        )
        self.read = self.enterContext(
            patch.object(shared, "get_resource", AsyncMock(return_value={"sharedService": self.firewall}))
        )
        self.failure = None
        self.restore_failure = None
        self.concurrent = False
        self.calls = []

        async def update(**kwargs):
            self.calls.append(deepcopy(kwargs))
            if len(self.calls) == 2 and self.restore_failure:
                raise self.restore_failure
            self.firewall["properties"].update(deepcopy(kwargs["payload"]["properties"]))
            self.firewall["_etag"] = "updated-etag"
            if len(self.calls) == 1:
                if self.concurrent:
                    self.firewall["properties"]["display_name"] = "Administrator edit"
                if self.failure:
                    raise self.failure

        self.post = self.enterContext(patch.object(shared, "post_resource", AsyncMock(side_effect=update)))

    async def test_missing_firewall_fails_without_patching(self):
        self.find.return_value = None
        with self.assertRaisesRegex(AssertionError, "Firewall shared service.*not found"):
            await shared.test_patch_firewall(True)
        self.post.assert_not_awaited()

    async def test_success_restores_original_properties_using_fresh_etag(self):
        await shared.test_patch_firewall(True)
        self.assertEqual(self.firewall["properties"], self.original)
        self.assertEqual([call["etag"] for call in self.calls], ["original-etag", "updated-etag"])
        self.assertEqual(len(self.calls[0]["payload"]["properties"]["rule_collections"]), 3)
        self.assertNotIn("private_ip", self.calls[1]["payload"]["properties"])
        self.read.assert_awaited_once_with("/api/shared-services/firewall-id", "token", True)

    async def test_failed_or_cancelled_patch_restores_original_properties(self):
        for error in (RuntimeError("PATCH_FAILED"), asyncio.CancelledError()):
            with self.subTest(error=type(error)):
                self.calls.clear()
                self.failure = error
                with self.assertRaises(type(error)) as caught:
                    await shared.test_patch_firewall(True)
                self.assertIs(caught.exception, error)
                self.assertEqual(self.firewall["properties"], self.original)

    async def test_restore_failure_fails_an_otherwise_successful_test(self):
        self.restore_failure = RuntimeError("RESTORE_FAILED")
        with self.assertRaisesRegex(RuntimeError, "RESTORE_FAILED"):
            await shared.test_patch_firewall(True)

    async def test_restore_failure_preserves_the_original_patch_error(self):
        self.failure = RuntimeError("PATCH_FAILED")
        self.restore_failure = RuntimeError("RESTORE_FAILED")
        with self.assertRaisesRegex(RuntimeError, "PATCH_FAILED") as caught:
            await shared.test_patch_firewall(True)
        self.assertIn("RESTORE_FAILED", caught.exception.__notes__[0])

    async def test_concurrent_edits_are_not_overwritten(self):
        self.concurrent = True
        with self.assertRaisesRegex(RuntimeError, "changed concurrently"):
            await shared.test_patch_firewall(True)
        self.assertEqual(self.firewall["properties"]["display_name"], "Administrator edit")
        self.assertEqual(len(self.calls), 1)
