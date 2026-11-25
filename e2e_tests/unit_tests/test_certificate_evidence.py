"""Check public certificate evidence, correlation and bounded cleanup reads."""

import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from httpx import AsyncClient, MockTransport, Response

from e2e_tests import bundle_evidence
from e2e_tests.resources import certificate as certs


SUBSCRIPTION = "11111111-1111-4111-8111-111111111111"
RESOURCE = "22222222-2222-4222-8222-222222222222"
WORKSPACE = "33333333-3333-4333-8333-333333333333"
TRE_ID = "testtre"
GROUP = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/rg-{TRE_ID}"
HOSTNAME = "nexus-testtre.switzerlandnorth.cloudapp.azure.com"


def gateway_certificate(*, hostname=HOSTNAME, days=90, pem=False):
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, hostname)])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=days))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(hostname)]), critical=False)
        .sign(key, hashes.SHA256())
    )
    encoding = serialization.Encoding.PEM if pem else serialization.Encoding.DER
    return base64.b64encode(certificate.public_bytes(encoding)).decode(), certificate.fingerprint(hashes.SHA256()).hex()


def resources(**kwargs):
    data, fingerprint = gateway_certificate(**kwargs)
    tags = {"tre_id": TRE_ID, "tre_shared_service_id": RESOURCE}
    gateway = {
        "id": f"{GROUP}/providers/Microsoft.Network/applicationGateways/agw-certs-{TRE_ID}",
        "tags": tags,
        "properties": {
            "operationalState": "Stopped",
            "sslCertificates": [
                {
                    "name": "cert-primary",
                    "properties": {
                        "keyVaultSecretId": f"https://kv-{TRE_ID}.vault.azure.net/secrets/nexus-ssl/abcd",
                        "publicCertData": data,
                    },
                }
            ],
        },
    }
    ip = {
        "id": f"{GROUP}/providers/Microsoft.Network/publicIPAddresses/pip-cert-nexus-{TRE_ID}",
        "tags": tags,
        "properties": {"dnsSettings": {"fqdn": HOSTNAME}},
    }
    return gateway, ip, fingerprint


def table(reused=1, issued=0, completed=1):
    return {
        "tables": [
            {
                "name": "PrimaryResult",
                "columns": [{"name": n} for n in ("reused", "issued", "completed")],
                "rows": [[reused, issued, completed]],
            }
        ]
    }


class CertificateMetadataTests(unittest.TestCase):
    def test_public_der_and_pem_produce_the_expected_sha256(self):
        for pem in (False, True):
            with self.subTest(pem=pem):
                gateway, ip, fingerprint = resources(pem=pem)
                self.assertEqual(
                    certs.certificate_metadata(gateway, ip, GROUP, TRE_ID, RESOURCE),
                    {"hostname": HOSTNAME, "sha256": fingerprint},
                )

    def test_rejects_wrong_hostname_and_certificate_due_for_renewal(self):
        for parameters in ({"hostname": "other.example.com"}, {"days": 29}):
            gateway, ip, _ = resources(**parameters)
            with self.subTest(parameters=parameters), self.assertRaises(AssertionError):
                certs.certificate_metadata(gateway, ip, GROUP, TRE_ID, RESOURCE)

    def test_rejects_unrelated_resource_and_vault_references(self):
        gateway, ip, _ = resources()
        changed = deepcopy(gateway)
        changed["tags"]["tre_shared_service_id"] = "another-resource"
        with self.assertRaisesRegex(AssertionError, "does not belong"):
            certs.certificate_metadata(changed, ip, GROUP, TRE_ID, RESOURCE)
        for uri in (
            "https://other.vault.azure.net/secrets/nexus-ssl/abcd",
            f"https://kv-{TRE_ID}.vault.azure.net/secrets/other/abcd",
            f"https://kv-{TRE_ID}.vault.azure.net/secrets/nexus-ssl/abcd?token=secret",
        ):
            changed = deepcopy(gateway)
            changed["properties"]["sslCertificates"][0]["properties"]["keyVaultSecretId"] = uri
            with self.subTest(uri=uri), self.assertRaisesRegex(AssertionError, "core vault"):
                certs.certificate_metadata(changed, ip, GROUP, TRE_ID, RESOURCE)

    def test_query_correlates_resource_trace_and_returns_only_counts(self):
        query = certs.reuse_query(RESOURCE, "a" * 64)
        self.assertIn(f"Message received for resource_id={RESOURCE},", query)
        self.assertIn("summarize", query)
        self.assertIn("join kind=leftsemi (received) on OperationId, ParentId", query)
        self.assertIn("join kind=leftsemi (installations) on OperationId, ParentId", query)
        self.assertIn(f"install action starting for {RESOURCE}...", query)
        self.assertIn("no ACME request required", query)
        with self.assertRaises(ValueError):
            certs.reuse_query("'; AppTraces", "a" * 64)
        with self.assertRaises(ValueError):
            certs.reuse_query(RESOURCE, "not-a-fingerprint")

    def test_partial_missing_or_malformed_logs_are_not_evidence(self):
        for response in (
            {},
            {**table(), "error": {"code": "PartialError"}},
            table(reused=True),
            table(issued=-1),
            {"tables": [{"name": "PrimaryResult", "rows": []}]},
        ):
            with self.subTest(response=response), self.assertRaises(RuntimeError):
                certs.query_counts(response)

    def test_report_drops_unapproved_metadata_and_raw_logs(self):
        with tempfile.TemporaryDirectory() as folder:
            report = bundle_evidence.BundleReport(Path(folder) / "report.json", {})
            with patch.object(bundle_evidence, "_ACTIVE_REPORT", report):
                bundle_evidence.record_certificate_check(
                    "reinstall",
                    f"/shared-services/{RESOURCE}",
                    {"hostname": HOSTNAME, "sha256": "a" * 64, "password": "do-not-copy", "logs": "do-not-copy"},
                    reused=True,
                )
            saved = json.loads(report.filename.read_text())
            self.assertTrue(saved["certificate_checks"][0]["reuse_confirmed"])
            self.assertNotIn("do-not-copy", report.filename.read_text())


class CertificateAzureReadTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.arm = SimpleNamespace(request=AsyncMock(), credential=Mock())
        self.checks = certs.CertificateChecks(self.arm, SUBSCRIPTION, TRE_ID)

    async def test_snapshot_waits_for_gateway_stop_and_reads_only_arm(self):
        gateway, ip, digest = resources()
        running = deepcopy(gateway)
        running["properties"]["operationalState"] = "Running"
        self.arm.request.side_effect = [running, gateway, ip]
        with patch.object(certs.asyncio, "sleep", AsyncMock()):
            result = await self.checks.snapshot(f"/shared-services/{RESOURCE}")
        self.assertEqual(result, {"hostname": HOSTNAME, "sha256": digest, "gateway_stopped": True})
        self.assertTrue(all(call.args[0] == "GET" for call in self.arm.request.await_args_list))
        self.assertTrue(all("Microsoft.Network/" in call.args[1] for call in self.arm.request.await_args_list))

    async def test_gateway_stop_has_a_finite_deadline(self):
        gateway, _, _ = resources()
        gateway["properties"]["operationalState"] = "Running"
        self.arm.request.return_value = gateway
        with patch.object(certs, "CHECK_TIMEOUT_SECONDS", 0.01), self.assertRaises(TimeoutError):
            await self.checks.snapshot(f"/shared-services/{RESOURCE}")

    async def test_log_ingestion_waits_for_reuse_and_completion(self):
        self.checks.query = AsyncMock(side_effect=[certs.query_counts(table(0, 0, 0)), certs.query_counts(table())])
        with patch.object(certs.asyncio, "sleep", AsyncMock()):
            await self.checks.confirm_reuse(f"/shared-services/{RESOURCE}", "a" * 64)
        self.assertEqual(self.checks.query.await_count, 2)

    async def test_issuance_and_missing_logs_fail_the_proof(self):
        self.checks.query = AsyncMock(return_value=certs.query_counts(table(1, 1, 1)))
        with self.assertRaisesRegex(AssertionError, "ACME issuance"):
            await self.checks.confirm_reuse(f"/shared-services/{RESOURCE}", "a" * 64)
        self.checks.query.return_value = certs.query_counts(table(0, 0, 0))
        with patch.object(certs, "CHECK_TIMEOUT_SECONDS", 0.01), self.assertRaises(TimeoutError):
            await self.checks.confirm_reuse(f"/shared-services/{RESOURCE}", "a" * 64)

    async def test_cleanup_requires_gateway_ip_and_storage_absence(self):
        self.arm.request.side_effect = [{"id": self.checks.gateway_id}, None, None, None, None, None]
        with patch.object(certs.asyncio, "sleep", AsyncMock()):
            await self.checks.confirm_removed()
        self.assertEqual(self.arm.request.await_count, 6)
        self.assertTrue(all(call.kwargs["missing_ok"] for call in self.arm.request.await_args_list))
        self.assertTrue(all(call.args[0] == "GET" for call in self.arm.request.await_args_list))

    async def test_failed_cleanup_read_is_not_treated_as_absence(self):
        self.arm.request.side_effect = RuntimeError("ARM GET failed with HTTP 403")
        with self.assertRaisesRegex(RuntimeError, "403"):
            await self.checks.confirm_removed()

    async def test_logs_query_does_not_follow_redirects_or_print_response_bodies(self):
        self.checks.logs_id = WORKSPACE
        self.arm.credential.get_token.return_value = SimpleNamespace(token="test-token")
        code = 200
        requests = []

        def handle(request):
            requests.append(request)
            if code != 200:
                return Response(code, headers={"location": "https://other.example.com"}, text="private-content")
            return Response(200, json=table())

        async with AsyncClient(transport=MockTransport(handle)) as client:
            self.arm.client = client
            self.assertEqual(await self.checks.query("query"), {"reused": 1, "issued": 0, "completed": 1})
            for code in (302, 403, 500):
                with self.subTest(code=code), self.assertRaisesRegex(RuntimeError, f"HTTP {code}") as caught:
                    await self.checks.query("query")
                self.assertNotIn("private-content", str(caught.exception))
        self.assertEqual(len(requests), 4)
        self.assertTrue(all(request.url.host == "api.loganalytics.azure.com" for request in requests))
        self.arm.credential.get_token.assert_called_with("https://api.loganalytics.io/.default")

    async def test_prepare_checks_logs_access_before_creating_resources(self):
        self.arm.request.return_value = {"properties": {"customerId": WORKSPACE}}
        self.checks.query = AsyncMock(return_value={"reused": 0, "issued": 0, "completed": 0})
        with patch.object(self.checks, "prepare_probe", AsyncMock()) as prepare_probe:
            await self.checks.prepare()
        prepare_probe.assert_awaited_once()
        self.assertEqual(self.checks.logs_id, WORKSPACE)
        self.checks.query.assert_awaited_once()
        self.assertEqual(self.arm.request.call_args.args[0], "GET")


class CertificateFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_or_empty_gateway_data_uses_the_exact_vault_reference(self):
        for missing in (None, ""):
            with self.subTest(missing=missing):
                gateway, ip, digest = resources()
                properties = gateway["properties"]["sslCertificates"][0]["properties"]
                data = properties.pop("publicCertData")
                if missing is not None:
                    properties["publicCertData"] = missing
                arm = SimpleNamespace(request=AsyncMock(side_effect=[gateway, ip]))
                checks = certs.CertificateChecks(arm, SUBSCRIPTION, TRE_ID)
                checks.public_certificate = AsyncMock(return_value=data)
                result = await checks.snapshot(f"/shared-services/{RESOURCE}")
                self.assertEqual(result, {"hostname": HOSTNAME, "sha256": digest, "gateway_stopped": True})
                checks.public_certificate.assert_awaited_once_with(properties["keyVaultSecretId"])

    async def test_fallback_keeps_hostname_and_validity_checks(self):
        for parameters in ({"hostname": "other.example.com"}, {"days": 29}):
            gateway, ip, _ = resources(**parameters)
            properties = gateway["properties"]["sslCertificates"][0]["properties"]
            data = properties.pop("publicCertData")
            arm = SimpleNamespace(request=AsyncMock(side_effect=[gateway, ip]))
            checks = certs.CertificateChecks(arm, SUBSCRIPTION, TRE_ID)
            checks.public_certificate = AsyncMock(return_value=data)
            with self.subTest(parameters=parameters), self.assertRaises(AssertionError):
                await checks.snapshot(f"/shared-services/{RESOURCE}")

    async def test_wrong_ownership_is_rejected_before_fallback(self):
        gateway, ip, _ = resources()
        gateway["tags"]["tre_id"] = "another-tre"
        arm = SimpleNamespace(request=AsyncMock(side_effect=[gateway, ip]))
        checks = certs.CertificateChecks(arm, SUBSCRIPTION, TRE_ID)
        checks.public_certificate = AsyncMock()
        with self.assertRaises(AssertionError):
            await checks.snapshot(f"/shared-services/{RESOURCE}")
        checks.public_certificate.assert_not_awaited()

    async def test_malformed_gateway_data_does_not_fall_back(self):
        gateway, ip, _ = resources()
        gateway["properties"]["sslCertificates"][0]["properties"]["publicCertData"] = "invalid!"
        arm = SimpleNamespace(request=AsyncMock(side_effect=[gateway, ip]))
        checks = certs.CertificateChecks(arm, SUBSCRIPTION, TRE_ID)
        checks.public_certificate = AsyncMock()
        with self.assertRaises(ValueError):
            await checks.snapshot(f"/shared-services/{RESOURCE}")
        checks.public_certificate.assert_not_awaited()
