"""Exercise certificate-only lifecycle boundaries without Azure access."""

import asyncio
import json
from pathlib import Path
from contextlib import asynccontextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from jsonschema import validate

from e2e_tests import test_shared_services as shared


class CertificateLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.date = self.enterContext(patch.object(shared, "date"))
        self.date.today.return_value.weekday.return_value = 0
        self.enterContext(patch.object(shared.config, "TEST_RUN_CERTIFICATE_TESTS_ON_WEEKENDS", False))
        self.enterContext(patch.object(shared.config, "TEST_ACCEPT_NEXUS_EULA", False))
        self.token = self.enterContext(patch.object(shared, "get_admin_token", AsyncMock(return_value="token")))
        self.find_service = self.enterContext(
            patch.object(shared, "get_shared_service_by_name", AsyncMock(return_value=None))
        )
        self.recover = self.enterContext(
            patch.object(shared, "disable_and_delete_shared_service_if_exists", AsyncMock())
        )
        self.post = self.enterContext(
            patch.object(
                shared,
                "post_resource",
                AsyncMock(
                    side_effect=[("/shared-services/certs", "certs"), ("/shared-services/reinstalled", "reinstalled")]
                ),
            )
        )
        self.cleanup = self.enterContext(patch.object(shared, "disable_and_delete_tre_resource", AsyncMock()))
        self.record = {
            "id": "certs",
            "templateName": shared.strings.CERTS_SHARED_SERVICE,
            "templateVersion": "0.9.0",
            "deploymentStatus": "deployed",
            "isEnabled": True,
            "properties": {"domain_prefix": "nexus", "cert_name": "nexus-ssl"},
        }
        self.template_version = "0.9.0"

        async def get_record(endpoint, *args):
            return {"sharedService": {**self.record, "id": endpoint.rsplit("/", 1)[-1]}}

        self.get = AsyncMock(side_effect=get_record)

        async def get_resource(endpoint, *args):
            if endpoint.startswith(shared.strings.API_SHARED_SERVICE_TEMPLATES):
                return {"name": shared.strings.CERTS_SHARED_SERVICE, "version": self.template_version}
            return await self.get(endpoint, *args)

        self.enterContext(patch.object(shared, "get_resource", get_resource))
        self.checks = SimpleNamespace(
            snapshot=AsyncMock(
                return_value={"hostname": "nexus-tre.test", "sha256": "a" * 64, "gateway_stopped": True}
            ),
            confirm_reuse=AsyncMock(),
            confirm_removed=AsyncMock(),
        )

        @asynccontextmanager
        async def checks():
            yield self.checks

        self.enterContext(patch.object(shared, "certificate_checks", checks))
        self.lookup_status = 404
        self.lookups = []

        def lookup(request):
            self.assertEqual(request.method, "GET")
            self.assertIn(request.url.path, ("/api/shared-services/certs", "/api/shared-services/reinstalled"))
            self.assertEqual(request.headers["Authorization"], "Bearer token")
            self.lookups.append(request)
            return httpx.Response(self.lookup_status, request=request)

        self.enterContext(
            patch.object(
                shared, "AsyncClient", lambda **kwargs: httpx.AsyncClient(transport=httpx.MockTransport(lookup))
            )
        )
        self.enterContext(patch.object(shared, "get_full_endpoint", lambda endpoint: "https://tre.test" + endpoint))

    async def test_creates_only_certificates_without_nexus_consent_and_confirms_removal(self):
        await shared.test_create_certificate_shared_service(True)
        self.assertEqual(self.post.await_count, 2)
        arguments = self.post.await_args.kwargs
        self.assertEqual(arguments["payload"]["templateName"], shared.strings.CERTS_SHARED_SERVICE)
        self.assertTrue(arguments["cleanup_failed_create"])
        schema = Path(__file__).resolve().parents[2] / "templates/shared_services/certs/template_schema.json"
        validate(arguments["payload"]["properties"], json.loads(schema.read_text()))
        self.recover.assert_awaited_once_with(shared.strings.CERTS_SHARED_SERVICE, True)
        self.assertEqual(self.cleanup.await_count, 2)
        self.assertEqual(len(self.lookups), 2)
        self.checks.confirm_removed.assert_awaited()
        self.assertEqual(self.checks.confirm_removed.await_count, 3)
        self.checks.confirm_reuse.assert_awaited_once_with("/shared-services/reinstalled", "a" * 64)

    async def test_existing_nexus_prevents_recovery_and_creation(self):
        self.find_service.return_value = {"id": "existing-nexus"}
        with self.assertRaisesRegex(pytest.fail.Exception, "Nexus is present"):
            await shared.test_create_certificate_shared_service(True)
        self.recover.assert_not_awaited()
        self.post.assert_not_awaited()
        self.cleanup.assert_not_awaited()

    async def test_weekend_skip_does_not_access_azure(self):
        for day in (5, 6):
            with self.subTest(day=day):
                self.date.today.return_value.weekday.return_value = day
                with self.assertRaisesRegex(pytest.skip.Exception, "coverage is unproven"):
                    await shared.test_create_certificate_shared_service(True)
        self.token.assert_not_awaited()
        self.recover.assert_not_awaited()
        self.post.assert_not_awaited()

    async def test_explicit_weekend_override_allows_the_certificate_case(self):
        self.date.today.return_value.weekday.return_value = 5
        with patch.object(shared.config, "TEST_RUN_CERTIFICATE_TESTS_ON_WEEKENDS", True):
            await shared.test_create_certificate_shared_service(True)
        self.assertEqual(self.post.await_count, 2)
        self.assertEqual(self.cleanup.await_count, 2)

    async def test_wrong_deployed_record_fails_and_still_cleans_up(self):
        self.record["deploymentStatus"] = "deployment_failed"
        with self.assertRaises(AssertionError):
            await shared.test_create_certificate_shared_service(True)
        self.cleanup.assert_awaited_once_with("/shared-services/certs", True)

    async def test_body_error_survives_a_cleanup_failure(self):
        failure = RuntimeError("Record lookup failed")
        self.get.side_effect = failure
        self.cleanup.side_effect = RuntimeError("Delete failed")
        with self.assertRaises(RuntimeError) as caught:
            await shared.test_create_certificate_shared_service(True)
        self.assertIs(caught.exception, failure)
        self.assertIn("Delete failed", failure.__notes__[0])

    async def test_nexus_appearing_during_the_case_retains_the_certificate(self):
        self.find_service.side_effect = [None, None, {"id": "new-nexus"}]
        with self.assertRaisesRegex(RuntimeError, "Retaining certificate dependency"):
            await shared.test_create_certificate_shared_service(True)
        self.cleanup.assert_not_awaited()
        self.assertEqual(self.lookups, [])

    async def test_visible_record_after_deletion_fails_the_case(self):
        for code in (200, 403, 500):
            with self.subTest(code=code):
                self.post.side_effect = [("/shared-services/certs", "certs")]
                self.lookup_status = code
                with self.assertRaisesRegex(AssertionError, f"HTTP {code}"):
                    await shared.test_create_certificate_shared_service(True)

    async def test_cleanup_uses_its_own_budget_after_validation_timeout(self):
        async def lookup(*args):
            await asyncio.sleep(60)

        async def cleanup(*args):
            await asyncio.sleep(0.03)

        self.get.side_effect = lookup
        self.cleanup.side_effect = cleanup
        with patch.object(shared, "CERTIFICATE_CHECK_TIMEOUT_SECONDS", 0.01):
            with self.assertRaises(TimeoutError):
                await shared.test_create_certificate_shared_service(True)
        self.cleanup.assert_awaited_once_with("/shared-services/certs", True)

    async def test_cancellation_still_cleans_up_the_owned_certificate(self):
        self.get.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await shared.test_create_certificate_shared_service(True)
        self.cleanup.assert_awaited_once_with("/shared-services/certs", True)

    async def test_creation_error_is_preserved_for_existing_failed_create_recovery(self):
        failure = RuntimeError("Certificate install failed")
        self.post.side_effect = failure
        with self.assertRaises(RuntimeError) as caught:
            await shared.test_create_certificate_shared_service(True)
        self.assertIs(caught.exception, failure)
        self.assertTrue(self.post.await_args.kwargs["cleanup_failed_create"])
        self.cleanup.assert_not_awaited()

    async def test_recovery_timeout_prevents_new_creation(self):
        async def recover(*args):
            await asyncio.sleep(60)

        self.recover.side_effect = recover
        with patch.object(shared, "RECOVERY_TIMEOUT_SECONDS", 0.01):
            with self.assertRaises(TimeoutError):
                await shared.test_create_certificate_shared_service(True)
        self.post.assert_not_awaited()

    async def test_old_bundle_fails_before_recovery_or_new_creation(self):
        for version in ("0.7.13", "0.8.9", "0.9.0-rc1", "invalid"):
            with self.subTest(version=version):
                self.template_version = version
                with self.assertRaisesRegex(pytest.fail.Exception, "Deploy the reuse fix first"):
                    await shared.test_create_certificate_shared_service(True)
        self.recover.assert_not_awaited()
        self.post.assert_not_awaited()

    async def test_changed_thumbprint_fails_and_cleans_both_installations(self):
        original = self.checks.snapshot.return_value
        self.checks.snapshot.side_effect = [original, {**original, "sha256": "b" * 64}]
        with self.assertRaisesRegex(AssertionError, "did not preserve"):
            await shared.test_create_certificate_shared_service(True)
        self.assertEqual(self.cleanup.await_count, 2)
        self.checks.confirm_reuse.assert_not_awaited()

    async def test_missing_reuse_log_fails_and_cleans_reinstalled_service(self):
        self.checks.confirm_reuse.side_effect = TimeoutError("No reuse evidence")
        with self.assertRaisesRegex(TimeoutError, "No reuse evidence"):
            await shared.test_create_certificate_shared_service(True)
        self.assertEqual(self.cleanup.await_count, 2)

    async def test_first_cleanup_failure_prevents_reinstallation(self):
        self.cleanup.side_effect = RuntimeError("Delete failed")
        with self.assertRaisesRegex(RuntimeError, "Delete failed"):
            await shared.test_create_certificate_shared_service(True)
        self.post.assert_awaited_once()

    async def test_arm_cleanup_failure_prevents_reinstallation(self):
        self.checks.confirm_removed.side_effect = [None, TimeoutError("Gateway remains")]
        with self.assertRaisesRegex(TimeoutError, "Gateway remains"):
            await shared.test_create_certificate_shared_service(True)
        self.post.assert_awaited_once()

    async def test_nexus_appearing_before_reinstall_prevents_new_creation(self):
        self.find_service.side_effect = [None, None, None, {"id": "new-nexus"}]
        with self.assertRaisesRegex(pytest.fail.Exception, "Nexus is present"):
            await shared.test_create_certificate_shared_service(True)
        self.post.assert_awaited_once()
        self.cleanup.assert_awaited_once()

    def test_lifecycle_timeout_leaves_job_setup_and_report_time(self):
        self.assertLess(shared.CERTIFICATE_LIFECYCLE_TIMEOUT_SECONDS, 290 * 60)
        required = (
            shared.CERTIFICATE_CHECK_TIMEOUT_SECONDS
            + shared.CERTIFICATE_RECOVERY_TIMEOUT_SECONDS
            + 2
            * (
                shared.CERTIFICATE_PROVISION_TIMEOUT_SECONDS
                + 3 * shared.CERTIFICATE_CHECK_TIMEOUT_SECONDS
                + max(shared.CLEANUP_TIMEOUT_SECONDS, shared.FAILED_CREATE_CLEANUP_TIMEOUT_SECONDS)
            )
        )
        self.assertGreater(shared.CERTIFICATE_LIFECYCLE_TIMEOUT_SECONDS, required)
