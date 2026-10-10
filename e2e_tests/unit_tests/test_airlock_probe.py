"""Check export probe evidence, token handling and bounded command cleanup."""

import asyncio
import base64
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from e2e_tests.resources import airlock_probe as probe


VM_ID = (
    "/subscriptions/00000000-0000-4000-8000-000000000000/resourceGroups/rg-tre-test-ws-1234"
    "/providers/Microsoft.Compute/virtualMachines/windowsvm1234"
)
PROBE_ID = "a" * 32
CONTENT = "Synthetic export data: café\n"
HASH = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()
CONTAINER_URL = "https://sttretest.blob.core.windows.net/export-draft?sp=rw&sig=private-sas-value"
PARAMETERS = {"phase": "read", "probe_id": PROBE_ID, "blob_name": "export-probe.txt", "content": CONTENT}


def result(**overrides):
    evidence = {"phase": "read", "probe": PROBE_ID, "sha256": HASH, **overrides}
    return {
        "properties": {
            "provisioningState": "Succeeded",
            "instanceView": {
                "executionState": "Succeeded",
                "exitCode": 0,
                "output": probe.MARKER + json.dumps(evidence),
            },
        }
    }


class ProbeEvidenceTests(unittest.TestCase):
    def check_result(self, resource):
        return probe.probe_result(resource, phase="read", probe_id=PROBE_ID, expected_hash=HASH)

    def test_exact_phase_probe_and_content_hash_are_required(self):
        self.assertTrue(self.check_result(result()))
        for changed in ({"phase": "upload"}, {"probe": "other"}, {"sha256": "0" * 64}, {"extra": True}):
            with self.subTest(changed=changed), self.assertRaises(AssertionError):
                self.check_result(result(**changed))

    def test_successful_provisioning_is_not_executed_probe_evidence(self):
        self.assertFalse(self.check_result({"properties": {"provisioningState": "Succeeded"}}))
        pending = result()
        pending["properties"]["instanceView"]["executionState"] = "Running"
        self.assertFalse(self.check_result(pending))

    def test_failure_exit_error_or_terminal_status_cannot_pass(self):
        changes = (
            {"executionState": "Failed"},
            {"executionState": "Canceled"},
            {"executionState": "TimedOut"},
            {"exitCode": 1},
            {"exitCode": False},
            {"error": "failure with a token that must not be included"},
        )
        for changed in changes:
            resource = result()
            resource["properties"]["instanceView"].update(changed)
            with self.subTest(changed=changed), self.assertRaises(AssertionError) as raised:
                self.check_result(resource)
            self.assertNotIn("token", str(raised.exception))
        resource = result()
        resource["properties"]["provisioningState"] = "Failed"
        with self.assertRaises(AssertionError):
            self.check_result(resource)

    def test_missing_duplicate_malformed_or_extra_output_cannot_pass(self):
        valid = result()["properties"]["instanceView"]["output"]
        duplicate_key = valid.replace('"phase": "read"', '"phase": "upload", "phase": "read"')
        for output in (
            "",
            valid + "\n" + valid,
            "noise\n" + valid,
            valid + "\nnoise",
            probe.MARKER + "{",
            duplicate_key,
            None,
        ):
            resource = result()
            resource["properties"]["instanceView"]["output"] = output
            with self.subTest(output=output), self.assertRaises(AssertionError):
                self.check_result(resource)


class ProbeCommandTests(unittest.IsolatedAsyncioTestCase):
    def make_arm(self, *responses):
        return SimpleNamespace(request=AsyncMock(side_effect=responses), delete=AsyncMock())

    async def run_probe(self, arm, **overrides):
        await probe.run_probe(arm, VM_ID, "switzerlandnorth", **{**PARAMETERS, **overrides})

    async def test_upload_keeps_sas_in_protected_parameters_and_sends_exact_utf8(self):
        arm = self.make_arm({}, result(phase="upload"))
        await self.run_probe(arm, phase="upload", container_url=CONTAINER_URL)
        create = arm.request.call_args_list[0]
        properties = deepcopy(create.kwargs["body"]["properties"])
        protected = properties.pop("protectedParameters")
        self.assertEqual(protected, [{"name": "ContainerUrl", "value": CONTAINER_URL}])
        self.assertNotIn("private-sas-value", json.dumps(properties))
        self.assertEqual(properties["source"]["script"], probe.SCRIPT.read_text())
        values = {item["name"]: item["value"] for item in properties["parameters"]}
        self.assertEqual(base64.b64decode(values["ContentBase64"]), CONTENT.encode("utf-8"))
        self.assertFalse(base64.b64decode(values["ContentBase64"]).startswith(b"\xef\xbb\xbf"))
        self.assertEqual(values["ExpectedSha256"], HASH)
        self.assertTrue(properties["treatFailureAsDeploymentFailure"])
        arm.delete.assert_awaited_once_with(create.args[1], probe.COMPUTE_API)

    async def test_read_has_no_download_url_and_waits_for_execution(self):
        arm = self.make_arm({}, {"properties": {"provisioningState": "Succeeded"}}, result())
        with patch.object(probe.asyncio, "sleep", AsyncMock()) as sleep:
            await self.run_probe(arm)
        properties = arm.request.call_args_list[0].kwargs["body"]["properties"]
        self.assertNotIn("protectedParameters", properties)
        self.assertNotIn("ContainerUrl", [item["name"] for item in properties["parameters"]])
        sleep.assert_awaited_once_with(10)
        self.assertEqual(arm.request.call_args.kwargs, {"expand": True})
        arm.delete.assert_awaited_once()

    async def test_hash_mismatch_or_command_failure_still_removes_the_command(self):
        failed = {"properties": {"instanceView": {"executionState": "Failed", "exitCode": 1}}}
        for response in (result(sha256="0" * 64), failed):
            arm = self.make_arm({}, response)
            with self.subTest(response=response), self.assertRaises(AssertionError):
                await self.run_probe(arm)
            command = arm.request.call_args_list[0].args[1]
            arm.delete.assert_awaited_once_with(command, probe.COMPUTE_API)

    async def test_accepted_put_with_lost_response_still_removes_the_command(self):
        arm = self.make_arm(TimeoutError("create response lost"))
        with self.assertRaisesRegex(TimeoutError, "create response lost"):
            await self.run_probe(arm)
        command = arm.request.call_args.args[1]
        arm.delete.assert_awaited_once_with(command, probe.COMPUTE_API)

    async def test_work_timeout_cleans_up_before_returning(self):
        async def blocked_request(*args, **kwargs):
            await asyncio.Event().wait()

        arm = SimpleNamespace(request=AsyncMock(side_effect=blocked_request), delete=AsyncMock())
        with patch.object(probe, "PROBE_TIMEOUT_SECONDS", 0.02), self.assertRaises(TimeoutError):
            await self.run_probe(arm)
        arm.delete.assert_awaited_once_with(arm.request.call_args.args[1], probe.COMPUTE_API)

    async def test_repeated_cancellation_waits_for_cleanup(self):
        request_started = asyncio.Event()
        cleanup_started = asyncio.Event()
        cleanup_release = asyncio.Event()
        removed = asyncio.Event()

        async def request(*args, **kwargs):
            request_started.set()
            await asyncio.Event().wait()

        async def delete(*args):
            cleanup_started.set()
            await cleanup_release.wait()
            removed.set()

        arm = SimpleNamespace(request=AsyncMock(side_effect=request), delete=AsyncMock(side_effect=delete))
        task = asyncio.create_task(self.run_probe(arm))
        await request_started.wait()
        task.cancel()
        await cleanup_started.wait()
        task.cancel()
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        cleanup_release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(removed.is_set())
        arm.delete.assert_awaited_once()

    async def test_invalid_parameters_never_create_a_command(self):
        cases = (
            {"phase": "download"},
            {"phase": "READ"},
            {"probe_id": "../../other"},
            {"blob_name": "../outside.txt"},
            {"blob_name": "folder/file.txt"},
            {"blob_name": "CON.txt"},
            {"blob_name": "file."},
            {"blob_name": "file:stream"},
            {"content": ""},
            {"content": "a" * 16385},
            {"content": b"data"},
            {"container_url": CONTAINER_URL},
            {"phase": "upload"},
        )
        for changed in cases:
            arm = self.make_arm()
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                await self.run_probe(arm, **changed)
            arm.request.assert_not_awaited()
            arm.delete.assert_not_awaited()
        for vm_id, location in ((VM_ID + "?other", "westeurope"), (VM_ID, "west europe")):
            arm = self.make_arm()
            with self.subTest(vm_id=vm_id, location=location), self.assertRaises(ValueError):
                await probe.run_probe(arm, vm_id, location, **PARAMETERS)
            arm.request.assert_not_awaited()

    async def test_untrusted_or_malformed_sas_urls_fail_without_echoing_tokens(self):
        urls = (
            CONTAINER_URL.replace("https://", "http://"),
            CONTAINER_URL.replace("blob.core.windows.net", "blob.core.windows.net.evil.test"),
            CONTAINER_URL.replace("export-draft?", "export-draft/other?"),
            CONTAINER_URL.replace("export-draft?", "export--draft?"),
            CONTAINER_URL.replace("export-draft?", "%2e%2e?"),
            CONTAINER_URL.replace("sig=", "not-sig="),
            CONTAINER_URL + "#private-sas-value",
            CONTAINER_URL + "&sig=private-sas-value",
            CONTAINER_URL.replace("sttretest.blob", "user@sttretest.blob"),
            CONTAINER_URL.replace("windows.net/", "windows.net:443/"),
            "https://[invalid?sig=private-sas-value",
        )
        for url in urls:
            arm = self.make_arm()
            with self.subTest(url=url), self.assertRaises(ValueError) as raised:
                await self.run_probe(arm, phase="upload", container_url=url)
            self.assertNotIn("private-sas-value", str(raised.exception))
            arm.request.assert_not_awaited()
