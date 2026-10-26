"""Check certificate-only reads, VM ownership and temporary command cleanup."""

import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from e2e_tests.resources import certificate as certs, certificate_probe as probe
from e2e_tests.unit_tests.test_certificate_evidence import SUBSCRIPTION, TRE_ID, GROUP, gateway_certificate


CLIENT_ID = "44444444-4444-4444-8444-444444444444"
CERTIFICATE_URL = f"https://kv-{TRE_ID}.vault.azure.net/certificates/nexus-ssl/abcd"
SECRET_ID = CERTIFICATE_URL.replace("/certificates/", "/secrets/")
VMSS = f"{GROUP}/providers/Microsoft.Compute/virtualMachineScaleSets/vmss-rp-porter-{TRE_ID}"
VM = VMSS + "/virtualMachines/0"
IDENTITY = f"{GROUP}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-vmss-{TRE_ID}"


class PublicCertificateScriptTests(unittest.TestCase):
    def certificate(self):
        return {
            "id": CERTIFICATE_URL,
            "sid": SECRET_ID,
            "cer": gateway_certificate()[0],
            "attributes": {"enabled": True},
            "private": "omit",
        }

    def test_reads_only_public_certificate_with_existing_identity(self):
        certificate = self.certificate()
        with patch.object(probe, "read_json", side_effect=[{"access_token": "token"}, certificate]) as read:
            output = probe.read_certificate(CERTIFICATE_URL, CLIENT_ID)
        saved = json.loads(output.removeprefix(probe.PREFIX))
        self.assertEqual(set(saved), {"id", "sid", "cer"})
        self.assertNotIn("token", output)
        self.assertNotIn("omit", output)
        self.assertEqual(read.call_args_list[0].args[0].host, "169.254.169.254")
        self.assertIn(CLIENT_ID, read.call_args_list[0].args[1])
        self.assertEqual(read.call_args_list[1].args[0].host, f"kv-{TRE_ID}.vault.azure.net")
        self.assertEqual(read.call_args_list[1].args[1], "/certificates/nexus-ssl/abcd?api-version=7.4")

    def test_rejects_other_hosts_secret_paths_unversioned_urls_and_invalid_identity(self):
        for url, identity in (
            (CERTIFICATE_URL.replace(".azure.net", ".example.com"), CLIENT_ID),
            (SECRET_ID, CLIENT_ID),
            (CERTIFICATE_URL.rsplit("/", 1)[0], CLIENT_ID),
            (CERTIFICATE_URL + "?other=true", CLIENT_ID),
            (CERTIFICATE_URL, "not-a-uuid"),
        ):
            with self.subTest(url=url, identity=identity), patch.object(probe, "read_json") as read:
                with self.assertRaises(ValueError):
                    probe.read_certificate(url, identity)
                read.assert_not_called()

    def test_rejects_disabled_mismatched_or_oversize_certificates(self):
        certificate = self.certificate()
        for changes in (
            {"id": CERTIFICATE_URL + "f"},
            {"sid": SECRET_ID + "f"},
            {"attributes": {"enabled": False}},
            {"cer": "invalid!"},
            {"cer": "A" * 5000},
        ):
            with (
                self.subTest(changes=list(changes)),
                patch.object(probe, "read_json", side_effect=[{"access_token": "token"}, {**certificate, **changes}]),
            ):
                with self.assertRaises(ValueError):
                    probe.read_certificate(CERTIFICATE_URL, CLIENT_ID)

    def test_redirects_and_failed_reads_are_not_followed_or_exposed(self):
        for code in (302, 403, 500):
            connection = Mock()
            connection.getresponse.return_value.status = code
            with self.subTest(code=code), self.assertRaisesRegex(RuntimeError, f"HTTP {code}"):
                probe.read_json(connection, "/certificates/nexus-ssl/abcd", {})
            connection.request.assert_called_once()
            connection.getresponse.return_value.read.assert_not_called()
            connection.close.assert_called_once()


class PublicCertificateCommandTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.arm = SimpleNamespace(request=AsyncMock(), delete=AsyncMock())
        self.checks = certs.CertificateChecks(self.arm, SUBSCRIPTION, TRE_ID)
        self.checks.probe_vm = (VM, "switzerlandnorth", CLIENT_ID)
        self.cer = gateway_certificate()[0]

    def result(self, **changes):
        result = {
            "executionState": "Succeeded",
            "exitCode": 0,
            "output": probe.PREFIX + json.dumps({"id": CERTIFICATE_URL, "sid": SECRET_ID, "cer": self.cer}),
        }
        result.update(changes)
        return {"properties": {"instanceView": result}}

    async def test_success_reads_exact_version_and_deletes_only_its_command(self):
        self.arm.request.side_effect = [{}, self.result()]
        result = await self.checks.public_certificate(SECRET_ID)
        self.assertEqual(result, self.cer)
        put = self.arm.request.call_args_list[0]
        self.assertEqual(put.args[0], "PUT")
        self.assertTrue(put.args[1].startswith(VM + "/runCommands/certificate-evidence-"))
        script = put.kwargs["body"]["properties"]["source"]["script"]
        self.assertIn(CERTIFICATE_URL, script)
        self.assertIn(CLIENT_ID, script)
        self.arm.delete.assert_awaited_once_with(put.args[1], certs.COMPUTE_API)

    async def test_failed_partial_or_wrong_version_evidence_still_cleans_up(self):
        for result in (
            self.result(executionState="Failed"),
            self.result(exitCode=1),
            self.result(output=""),
            self.result(
                output=probe.PREFIX + json.dumps({"id": CERTIFICATE_URL + "f", "sid": SECRET_ID, "cer": self.cer})
            ),
        ):
            self.arm.delete.reset_mock()
            self.arm.request.side_effect = [{}, result]
            with (
                self.subTest(result=result["properties"]["instanceView"]["executionState"]),
                self.assertRaises((RuntimeError, ValueError)),
            ):
                await self.checks.public_certificate(SECRET_ID)
            self.arm.delete.assert_awaited_once()

    async def test_cancellation_after_put_still_deletes_command(self):
        self.arm.request.side_effect = [{}, asyncio.CancelledError()]
        with self.assertRaises(asyncio.CancelledError):
            await self.checks.public_certificate(SECRET_ID)
        self.arm.delete.assert_awaited_once()

    async def test_rejects_unrelated_vault_before_creating_command(self):
        with self.assertRaises(ValueError):
            await self.checks.public_certificate(SECRET_ID.replace(TRE_ID, "another-tre"))
        self.arm.request.assert_not_awaited()

    async def test_prepare_requires_owned_running_vm_and_expected_identity(self):
        vmss = {
            "id": VMSS,
            "location": "switzerlandnorth",
            "tags": {"tre_id": TRE_ID},
            "identity": {"userAssignedIdentities": {IDENTITY: {"clientId": CLIENT_ID}}},
        }
        instances = {"value": [{"id": VM}]}
        running = {"statuses": [{"code": "PowerState/running"}]}
        self.arm.request.side_effect = [vmss, instances, running]
        await self.checks.prepare_probe()
        self.assertEqual(self.checks.probe_vm, (VM, "switzerlandnorth", CLIENT_ID))
        for changed in ({**vmss, "tags": {"tre_id": "other"}}, {**vmss, "identity": {}}):
            self.arm.request.side_effect = [changed]
            with self.assertRaises(AssertionError):
                await self.checks.prepare_probe()
        self.arm.request.side_effect = [deepcopy(vmss), {"value": [{"id": VM.replace("/0", "/../another")}]}]
        with self.assertRaises(ValueError):
            await self.checks.prepare_probe()
        self.arm.request.side_effect = [vmss, instances, {"statuses": [{"code": "PowerState/deallocated"}]}]
        with self.assertRaisesRegex(RuntimeError, "No running"):
            await self.checks.prepare_probe()
