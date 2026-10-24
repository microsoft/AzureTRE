"""Check the Gitea probe's evidence, payloads and cleanup boundaries."""

import json
from pathlib import Path, PurePosixPath
import re
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from jsonschema import validate
import yaml

from api_app.services.schema_service import enrich_user_resource_template, enrich_workspace_service_template
from e2e_tests import test_gitea as gitea
from e2e_tests.resources import gitea_probe as probe


ROOT = Path(__file__).resolve().parents[2]
GROUP = "/subscriptions/sub/resourceGroups/rg-tretest-ws-abcd"
VM_ID = f"{GROUP}/providers/Microsoft.Compute/virtualMachines/windowsvm1234"
GITEA_URL = "https://gitea-tretest-ws-abcd-svc-1234.azurewebsites.net"
PROBE_ID = "0123456789abcdef0123456789abcdef"
PROBE = {
    "gitea_url": GITEA_URL,
    "vault_name": "kv-tretest-ws-abcd",
    "secret_name": "gitea-tretest-ws-abcd-svc-1234-administrator-password",
    "probe_id": PROBE_ID,
}


def result(evidence, state="Succeeded", code=0, output=None):
    return {
        "properties": {
            "provisioningState": "Succeeded",
            "instanceView": {
                "executionState": state,
                "exitCode": code,
                "output": output if output is not None else "GITEA_PROBE_RESULT=" + json.dumps(evidence),
            },
        }
    }


class ProbeEvidenceTests(unittest.TestCase):
    def test_write_phase_requires_denied_requests_and_the_commit(self):
        evidence = probe.expected_result("write", PROBE_ID)
        self.assertEqual(evidence["anonymous_create"], 401)
        self.assertEqual(evidence["wrong_password"], 401)
        self.assertEqual(evidence["anonymous_read"], 404)
        self.assertTrue(probe.probe_result(result(evidence), "write", PROBE_ID))
        for change in (
            {"anonymous_create": 201},
            {"wrong_password": 200},
            {"anonymous_read": 200},
            {"content": False},
            {"private_dns": False},
        ):
            with self.subTest(change=change), self.assertRaises(AssertionError):
                probe.probe_result(result({**evidence, **change}), "write", PROBE_ID)

    def test_read_phase_requires_the_file_and_the_delete(self):
        evidence = probe.expected_result("read", PROBE_ID)
        self.assertTrue(probe.probe_result(result(evidence), "read", PROBE_ID))
        for change in ({"content": False}, {"deleted": False}):
            with self.subTest(change=change), self.assertRaises(AssertionError):
                probe.probe_result(result({**evidence, **change}), "read", PROBE_ID)
        with self.assertRaises(AssertionError):
            probe.probe_result(result(probe.expected_result("write", PROBE_ID)), "read", PROBE_ID)

    def test_running_command_is_not_a_pass_and_failure_names_the_stage(self):
        running = result({})
        running["properties"]["instanceView"] = {}
        self.assertFalse(probe.probe_result(running, "write", PROBE_ID))
        failed = result({}, state="Failed", code=1, output="GITEA_PROBE_FAILED=gitea-admin\n")
        with self.assertRaisesRegex(AssertionError, "stage=gitea-admin"):
            probe.probe_result(failed, "write", PROBE_ID)

    def test_payloads_match_enriched_api_schemas(self):
        cases = (
            (gitea.GITEA_PAYLOAD, "gitea", enrich_workspace_service_template),
            (gitea.VM_PAYLOAD, "guacamole/user_resources/guacamole-azure-windowsvm", enrich_user_resource_template),
        )
        for payload, folder, enrich in cases:
            with self.subTest(bundle=payload["templateName"]):
                schema = json.loads(
                    (ROOT / "templates/workspace_services" / folder / "template_schema.json").read_text()
                )
                validate(payload["properties"], enrich(SimpleNamespace(model_dump=lambda **_: schema)))
        self.assertFalse(any(v for k, v in gitea.VM_PAYLOAD["properties"].items() if k.startswith("install_")))

    def test_deadline_precedes_container(self):
        jobs = yaml.safe_load((ROOT / ".github/workflows/deploy_tre_reusable.yml").read_text())["jobs"]
        job = jobs["e2e_tests_bundle"]
        reserve = next(s for s in job["steps"] if "GITEA_VALIDATION_DEADLINE" in s.get("run", ""))
        run = next(s for s in job["steps"] if s["name"] == "Run E2E Tests")
        self.assertLess(job["steps"].index(reserve), job["steps"].index(run))
        self.assertEqual(reserve["if"], "inputs.e2eBundle == 'tre-workspace-service-gitea'")
        self.assertIn("GITEA_VALIDATION_DEADLINE=${{ env.GITEA_VALIDATION_DEADLINE }}", run["with"]["COMMAND"])

    def test_script_accepts_the_names_that_the_test_builds(self):
        # The script rejects a parameter that does not match its pattern.
        found = re.findall(r"ValidatePattern\('([^']+)'\)\]\[string\]\$(\w+)", probe.SCRIPT.read_text())
        patterns = {name: pattern for pattern, name in found}
        values = {**PROBE, "probe_id": uuid4().hex}
        for name, key in (("GiteaUrl", "gitea_url"), ("VaultName", "vault_name"), ("SecretName", "secret_name")):
            with self.subTest(name=name):
                self.assertRegex(values[key], patterns[name])
        self.assertRegex(values["probe_id"], patterns["ProbeId"])

    def test_script_offers_the_tls_version_that_the_web_app_requires(self):
        # A TLS handshake failure leaves no request in the web app logs.
        webapp = (ROOT / "templates/workspace_services/gitea/terraform/gitea-webapp.tf").read_text()
        version = re.search(r'minimum_tls_version\s*=\s*"1\.(\d)"', webapp).group(1)
        self.assertIn(f"[Net.SecurityProtocolType]::Tls1{version}", probe.SCRIPT.read_text())

    def test_repositories_are_on_the_file_share(self):
        # The read phase runs after a restart, and a restart deletes the data outside the share.
        webapp = (ROOT / "templates/workspace_services/gitea/terraform/gitea-webapp.tf").read_text()
        mount = re.search(r'mount_path\s*=\s*"([^"]+)"', webapp).group(1)
        repositories = re.search(r'GITEA__repository__ROOT\s*=\s*"([^"]+)"', webapp).group(1)
        self.assertIn(PurePosixPath(mount), PurePosixPath(repositories).parents)


class ProbeRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_command_is_removed(self):
        failed = result({}, state="Failed", code=1, output="GITEA_PROBE_FAILED=secret-access\n")
        arm = SimpleNamespace(request=AsyncMock(side_effect=[{}, failed]), delete=AsyncMock())
        with self.assertRaisesRegex(AssertionError, "secret-access"):
            await probe.run_probe(arm, VM_ID, "switzerlandnorth", **PROBE, phase="write")
        command = arm.request.call_args_list[0].args[1]
        self.assertTrue(command.startswith(VM_ID + "/runCommands/gitea-probe-"))
        arm.delete.assert_awaited_once_with(command, probe.COMPUTE_API)
        parameters = arm.request.call_args_list[0].kwargs["body"]["properties"]["parameters"]
        self.assertEqual(
            {p["name"]: p["value"] for p in parameters},
            {
                "GiteaUrl": GITEA_URL,
                "VaultName": PROBE["vault_name"],
                "SecretName": PROBE["secret_name"],
                "ProbeId": PROBE_ID,
                "Phase": "write",
            },
        )
