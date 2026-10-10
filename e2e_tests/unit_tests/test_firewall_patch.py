"""Ensure firewall selection cannot pass without exercising its target."""

import unittest
from unittest.mock import AsyncMock, patch

from e2e_tests import test_shared_services


class FirewallPatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_firewall_fails_without_patching(self):
        for missing in (None, {}):
            with (
                self.subTest(service=missing),
                patch.object(test_shared_services, "get_admin_token", AsyncMock(return_value="token")),
                patch.object(test_shared_services, "get_shared_service_by_name", AsyncMock(return_value=missing)),
                patch.object(test_shared_services, "post_resource", AsyncMock()) as post,
            ):
                with self.assertRaisesRegex(AssertionError, "Firewall shared service.*not found"):
                    await test_shared_services.test_patch_firewall(verify=True)
                post.assert_not_awaited()

    async def test_existing_firewall_is_patched_with_its_etag(self):
        firewall = {"id": "firewall-id", "_etag": "etag"}
        with (
            patch.object(test_shared_services, "get_admin_token", AsyncMock(return_value="token")),
            patch.object(test_shared_services, "get_shared_service_by_name", AsyncMock(return_value=firewall)),
            patch.object(test_shared_services, "post_resource", AsyncMock()) as post,
        ):
            await test_shared_services.test_patch_firewall(verify=True)
        post.assert_awaited_once()
        self.assertEqual(post.call_args.kwargs["endpoint"], "/api/shared-services/firewall-id")
        self.assertEqual(post.call_args.kwargs["method"], "PATCH")
        self.assertEqual(post.call_args.kwargs["etag"], "etag")
        self.assertEqual(len(post.call_args.kwargs["payload"]["properties"]["rule_collections"]), 3)

    async def test_failed_patch_remains_a_test_failure(self):
        with (
            patch.object(test_shared_services, "get_admin_token", AsyncMock(return_value="token")),
            patch.object(
                test_shared_services,
                "get_shared_service_by_name",
                AsyncMock(return_value={"id": "fw", "_etag": "etag"}),
            ),
            patch.object(test_shared_services, "post_resource", AsyncMock(side_effect=RuntimeError("PATCH_FAILED"))),
        ):
            with self.assertRaisesRegex(RuntimeError, "PATCH_FAILED"):
                await test_shared_services.test_patch_firewall(verify=True)
