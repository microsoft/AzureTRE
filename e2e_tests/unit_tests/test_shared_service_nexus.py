"""Check explicit Nexus consent before shared-service lifecycle mutations."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import pytest
from jsonschema import validate

from e2e_tests import test_shared_services as shared


class SharedServiceNexusConsentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.date = self.enterContext(patch.object(shared, "date"))
        self.date.today.return_value.weekday.return_value = 0
        self.cleanup_existing = self.enterContext(
            patch.object(shared, "disable_and_delete_shared_service_if_exists", new=AsyncMock())
        )
        self.token = self.enterContext(patch.object(shared, "get_admin_token", new=AsyncMock(return_value="token")))
        self.post = self.enterContext(
            patch.object(
                shared,
                "post_resource",
                new=AsyncMock(side_effect=[("/shared-services/certs", "certs"), ("/shared-services/nexus", "nexus")]),
            )
        )
        self.cleanup_created = self.enterContext(
            patch.object(shared, "disable_and_delete_tre_resource", new=AsyncMock())
        )

    async def test_missing_consent_fails_before_azure_access_even_on_weekends(self):
        for day in (0, 5, 6):
            with self.subTest(day=day), patch.object(shared.config, "TEST_ACCEPT_NEXUS_EULA", False):
                self.date.today.return_value.weekday.return_value = day
                with self.assertRaisesRegex(pytest.fail.Exception, "acceptance is required.*coverage is unproven"):
                    await shared.test_create_certs_nexus_shared_service(True)
        self.cleanup_existing.assert_not_awaited()
        self.token.assert_not_awaited()
        self.post.assert_not_awaited()
        self.cleanup_created.assert_not_awaited()

    async def test_explicit_consent_reaches_schema_valid_nexus_payload(self):
        with patch.object(shared.config, "TEST_ACCEPT_NEXUS_EULA", True):
            await shared.test_create_certs_nexus_shared_service(True)
        payloads = [call.kwargs["payload"] for call in self.post.await_args_list]
        self.assertEqual(
            [payload["templateName"] for payload in payloads],
            [
                shared.strings.CERTS_SHARED_SERVICE,
                shared.strings.NEXUS_SHARED_SERVICE,
            ],
        )
        schema_file = (
            Path(__file__).resolve().parents[2] / "templates/shared_services/sonatype-nexus-vm/template_schema.json"
        )
        validate(payloads[1]["properties"], json.loads(schema_file.read_text()))
        self.assertIs(payloads[1]["properties"]["accept_nexus_eula"], True)
        self.assertEqual(payloads[1]["properties"].get("vm_size"), "Standard_D2s_v3")
        self.assertEqual(
            [call.args[0] for call in self.cleanup_created.await_args_list],
            ["/shared-services/nexus", "/shared-services/certs"],
        )

    async def test_weekend_skip_with_consent_still_leaves_resources_unchanged(self):
        self.date.today.return_value.weekday.return_value = 5
        with patch.object(shared.config, "TEST_ACCEPT_NEXUS_EULA", True):
            with self.assertRaisesRegex(pytest.skip.Exception, "coverage is unproven"):
                await shared.test_create_certs_nexus_shared_service(True)
        self.cleanup_existing.assert_not_awaited()
        self.token.assert_not_awaited()
        self.post.assert_not_awaited()


class NexusConsentConfigurationTests(unittest.TestCase):
    def test_absent_false_and_explicit_true_configuration(self):
        root = Path(__file__).resolve().parents[2]
        for value, expected in ((None, "False"), ("false", "False"), ("true", "True")):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                env = dict(os.environ, PYTHONPATH=str(root))
                env.pop("TEST_ACCEPT_NEXUS_EULA", None)
                if value is not None:
                    env["TEST_ACCEPT_NEXUS_EULA"] = value
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "from e2e_tests.config import TEST_ACCEPT_NEXUS_EULA; print(TEST_ACCEPT_NEXUS_EULA)",
                    ],
                    env=env,
                    cwd=directory,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10,
                )
                self.assertEqual(result.stdout.strip(), expected)
