"""Check explicit Nexus consent before shared-service lifecycle mutations."""

import asyncio
import json
import os
import re
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
        self.enterContext(patch.object(shared.config, "TEST_RUN_CERTIFICATE_TESTS_ON_WEEKENDS", False))
        self.cleanup_existing = self.enterContext(
            patch.object(shared, "disable_and_delete_shared_service_if_exists", new=AsyncMock())
        )
        self.token = self.enterContext(patch.object(shared, "get_admin_token", new=AsyncMock(return_value="token")))
        self.find_service = self.enterContext(
            patch.object(shared, "get_shared_service_by_name", AsyncMock(return_value=None))
        )
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

    async def test_previous_resources_share_one_recovery_deadline_before_new_creation(self):
        async def recover(name, verify):
            if name == shared.strings.NEXUS_SHARED_SERVICE:
                await asyncio.sleep(0.01)
            else:
                await asyncio.sleep(1)

        self.cleanup_existing.side_effect = recover
        with (
            patch.object(shared.config, "TEST_ACCEPT_NEXUS_EULA", True),
            patch.object(shared, "RECOVERY_TIMEOUT_SECONDS", 0.03),
        ):
            with self.assertRaises(TimeoutError):
                await shared.test_create_certs_nexus_shared_service(True)
        self.assertEqual(self.cleanup_existing.await_count, 2)
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

    async def test_explicit_weekend_override_runs_certificate_lifecycle(self):
        self.date.today.return_value.weekday.return_value = 5
        with (
            patch.object(shared.config, "TEST_ACCEPT_NEXUS_EULA", True),
            patch.object(shared.config, "TEST_RUN_CERTIFICATE_TESTS_ON_WEEKENDS", True),
        ):
            await shared.test_create_certs_nexus_shared_service(True)
        self.assertEqual(self.post.await_count, 2)
        self.assertEqual(self.cleanup_created.await_count, 2)

    async def test_provisioning_timeout_leaves_time_for_certificate_cleanup(self):
        async def deploy(*, payload, **kwargs):
            if payload["templateName"] == shared.strings.CERTS_SHARED_SERVICE:
                return "/shared-services/certs", "certs"
            await asyncio.sleep(60)
            return "/shared-services/nexus", "nexus"

        async def cleanup(*args):
            await asyncio.sleep(0.03)

        self.post.side_effect = deploy
        self.cleanup_created.side_effect = cleanup
        with (
            patch.object(shared.config, "TEST_ACCEPT_NEXUS_EULA", True),
            patch.object(shared, "PROVISIONING_TIMEOUT_SECONDS", 0.01),
        ):
            with self.assertRaises(TimeoutError):
                await shared.test_create_certs_nexus_shared_service(True)
        self.cleanup_created.assert_awaited_once_with("/shared-services/certs", True)

    async def test_successful_provisioning_cleanup_outlives_provisioning_deadline(self):
        async def cleanup(*args):
            await asyncio.sleep(0.02)

        self.cleanup_created.side_effect = cleanup
        with (
            patch.object(shared.config, "TEST_ACCEPT_NEXUS_EULA", True),
            patch.object(shared, "PROVISIONING_TIMEOUT_SECONDS", 0.01),
        ):
            await shared.test_create_certs_nexus_shared_service(True)
        self.assertEqual(
            [call.args[0] for call in self.cleanup_created.await_args_list],
            ["/shared-services/nexus", "/shared-services/certs"],
        )

    async def test_cleanup_timeout_is_reported_and_remaining_cleanup_is_attempted(self):
        async def cleanup(path, verify):
            if path.endswith("nexus"):
                await asyncio.sleep(60)

        self.cleanup_created.side_effect = cleanup
        with (
            patch.object(shared.config, "TEST_ACCEPT_NEXUS_EULA", True),
            patch.object(shared, "CLEANUP_TIMEOUT_SECONDS", 0.01),
        ):
            with self.assertRaises(TimeoutError):
                await shared.test_create_certs_nexus_shared_service(True)
        self.assertEqual(self.cleanup_created.await_count, 2)

    async def test_cleanup_failure_does_not_replace_provisioning_error(self):
        failure = RuntimeError("Nexus deployment failed")
        self.post.side_effect = [("/shared-services/certs", "certs"), failure]
        self.cleanup_created.side_effect = RuntimeError("Certificate cleanup failed")
        with patch.object(shared.config, "TEST_ACCEPT_NEXUS_EULA", True):
            with self.assertRaises(RuntimeError) as caught:
                await shared.test_create_certs_nexus_shared_service(True)
        self.assertIs(caught.exception, failure)
        self.assertIn("/shared-services/certs", caught.exception.__notes__[0])

    async def test_certificate_is_retained_when_nexus_cleanup_failed(self):
        failure = RuntimeError("Nexus cleanup failed")
        self.cleanup_created.side_effect = failure
        self.find_service.return_value = {"id": "nexus"}
        with patch.object(shared.config, "TEST_ACCEPT_NEXUS_EULA", True):
            with self.assertRaises(RuntimeError) as caught:
                await shared.test_create_certs_nexus_shared_service(True)
        self.assertIs(caught.exception, failure)
        self.cleanup_created.assert_awaited_once_with("/shared-services/nexus", True)
        self.assertIn("Retaining certificate dependency", caught.exception.__notes__[0])


class ExistingSharedServiceRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_unrelated_service_is_preserved(self):
        service = {"id": "existing", "properties": {"display_name": "Retain this service"}}
        with (
            patch.object(shared, "get_admin_token", AsyncMock(return_value="token")),
            patch.object(shared, "get_shared_service_by_name", AsyncMock(return_value=service)),
            patch.object(shared, "disable_and_delete_resource", AsyncMock()) as cleanup,
        ):
            with self.assertRaisesRegex(AssertionError, "not created by this test"):
                await shared.disable_and_delete_shared_service_if_exists(shared.strings.CERTS_SHARED_SERVICE, True)
        cleanup.assert_not_awaited()

    async def test_old_test_resource_waits_for_terminal_operation_before_recovery(self):
        name = shared.strings.CERTS_SHARED_SERVICE
        service = {
            "id": "certs",
            "properties": {
                "display_name": f"Shared service {name}",
                "description": f"{name} deployed via e2e tests",
            },
        }
        events = []

        async def operations(*args):
            events.append("poll")
            return {"operations": [{"status": "pipeline_running" if len(events) == 1 else "updated"}]}

        async def cleanup(*args, **kwargs):
            events.append("delete")

        with (
            patch.object(shared, "get_admin_token", AsyncMock(return_value="token")),
            patch.object(shared, "get_shared_service_by_name", AsyncMock(return_value=service)),
            patch.object(shared, "get_resource", operations),
            patch.object(shared.asyncio, "sleep", AsyncMock()),
            patch.object(shared, "disable_and_delete_resource", cleanup),
        ):
            await shared.disable_and_delete_shared_service_if_exists(name, True)
        self.assertEqual(events, ["poll", "poll", "delete"])


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


class SharedServiceWorkflowBudgetTests(unittest.TestCase):
    def test_outer_watchdogs_include_failed_create_and_final_cleanup_with_job_margin(self):
        single = next(mark.args[0] for mark in shared.test_create_shared_service.pytestmark if mark.name == "timeout")
        nexus = next(
            mark.args[0] for mark in shared.test_create_certs_nexus_shared_service.pytestmark if mark.name == "timeout"
        )
        setup = shared.RECOVERY_TIMEOUT_SECONDS + shared.PROVISIONING_TIMEOUT_SECONDS
        self.assertGreater(
            single, setup + max(shared.CLEANUP_TIMEOUT_SECONDS, shared.FAILED_CREATE_CLEANUP_TIMEOUT_SECONDS)
        )
        self.assertGreater(nexus, setup + 2 * shared.CLEANUP_TIMEOUT_SECONDS)
        self.assertGreater(nexus, setup + shared.FAILED_CREATE_CLEANUP_TIMEOUT_SECONDS + shared.CLEANUP_TIMEOUT_SECONDS)
        workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/deploy_tre_reusable.yml").read_text()
        job_minutes = int(re.search(r"(?s)  e2e_tests_custom:\n.*?    timeout-minutes: (\d+)", workflow).group(1))
        self.assertGreaterEqual(job_minutes * 60 - nexus, 30 * 60)

    def test_main_selection_without_consent_excludes_only_nexus_from_shared_services(self):
        root = Path(__file__).resolve().parents[2]
        environment = dict(os.environ, PYTHONPATH=os.pathsep.join((str(root), str(root / "e2e_tests"))))
        environment.pop("PYTEST_ADDOPTS", None)
        for selector, expected_count in (("shared_services", 5), ("shared_services and not nexus", 4)):
            with self.subTest(selector=selector):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "--collect-only",
                        "-q",
                        "-o",
                        "addopts=",
                        "-m",
                        selector,
                        "test_shared_services.py",
                    ],
                    cwd=root / "e2e_tests",
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                selected = [line for line in result.stdout.splitlines() if line.startswith("test_shared_services.py::")]
                self.assertEqual(len(selected), expected_count, result.stdout)
                self.assertEqual(
                    any("test_create_certs_nexus_shared_service" in line for line in selected), expected_count == 5
                )
