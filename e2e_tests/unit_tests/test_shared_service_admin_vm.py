"""Prevent shared-service tests from reverting to the restricted admin VM size."""

import json
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from jsonschema import validate

from e2e_tests import test_shared_services as shared


class SharedServiceAdminVmTests(unittest.IsolatedAsyncioTestCase):
    async def test_admin_vm_payload_selects_available_schema_valid_size(self):
        with (
            patch.object(shared, "disable_and_delete_shared_service_if_exists", new=AsyncMock()),
            patch.object(shared, "get_admin_token", new=AsyncMock(return_value="token")),
            patch.object(
                shared,
                "post_resource",
                new=AsyncMock(return_value=("/shared-services/admin-vm", "admin-vm")),
            ) as post,
            patch.object(shared, "disable_and_delete_tre_resource", new=AsyncMock()),
        ):
            await shared.test_create_shared_service(shared.strings.ADMIN_VM_SHARED_SERVICE, True)

        post.assert_awaited_once()
        payload = post.await_args.kwargs["payload"]
        self.assertEqual(payload["templateName"], shared.strings.ADMIN_VM_SHARED_SERVICE)
        self.assertEqual(payload["properties"].get("admin_jumpbox_vm_sku"), "Standard_D2s_v3")
        schema_file = Path(__file__).resolve().parents[2] / "templates/shared_services/admin-vm/template_schema.json"
        validate(payload["properties"], json.loads(schema_file.read_text()))
