"""Check the MySQL probe's evidence, input handling and cleanup boundaries."""

import json
import os
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from jsonschema import validate
import yaml

from api_app.services.schema_service import enrich_user_resource_template, enrich_workspace_service_template
from e2e_tests import test_mysql as mysql
from e2e_tests.resources import mysql_probe as probe
from e2e_tests.resources import sql_lifecycle as lifecycle


ROOT = Path(__file__).resolve().parents[2]
VM_ID = "/subscriptions/sub/resourceGroups/rg-tretest-ws-abcd/providers/Microsoft.Compute/virtualMachines/linuxvm1234"
PROBE_ID = "0123456789abcdef0123456789abcdef"
VALUES = {
    "SERVER": "mysql-tretest-ws-abcd-svc-1234.mysql.database.azure.com",
    "VAULT_NAME": "kv-tretest-ws-abcd",
    "SECRET_NAME": "mysql-tretest-ws-abcd-svc-1234-administrator-password",
    "DATABASE": "tredb",
    "PROBE_ID": PROBE_ID,
    "PHASE": "read",
}


def result(output=None, state="Succeeded", code=0, **overrides):
    evidence = {"phase": "read", "probe": PROBE_ID, "row_count": 1, "private_dns": True, **overrides}
    return {
        "properties": {
            "provisioningState": "Succeeded",
            "instanceView": {
                "executionState": state,
                "exitCode": code,
                "output": output if output is not None else "MYSQL_PROBE_RESULT=" + json.dumps(evidence),
            },
        }
    }


class ProbeScriptTests(unittest.TestCase):
    def test_script_sets_only_validated_values(self):
        script = probe.probe_script(**VALUES)
        self.assertTrue(script.startswith("#!/usr/bin/env bash\n"))
        self.assertEqual(script.count("#!"), 1)
        for name, value in VALUES.items():
            self.assertIn(f"{name}='{value}'\n", script)
        self.assertNotIn("password=", script.split("set -euo pipefail")[0])

    def test_unexpected_or_unsafe_values_are_rejected(self):
        for name, value in (
            ("SERVER", "evil.example.com"),
            ("SERVER", "a'; reboot; '.mysql.database.azure.com"),
            ("DATABASE", "tredb; DROP DATABASE mysql"),
            ("PROBE_ID", "abc"),
            ("PHASE", "delete"),
        ):
            with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                probe.probe_script(**{**VALUES, name: value})
        with self.assertRaises(ValueError):
            probe.probe_script(**{k: v for k, v in VALUES.items() if k != "PHASE"})

    def test_script_is_valid_bash(self):
        completed = subprocess.run(
            ["bash", "-n"], input=probe.probe_script(**VALUES), text=True, capture_output=True, check=False
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_script_rejects_values_that_skip_python_validation(self):
        script = probe.probe_script(**VALUES).replace("PHASE='read'", "PHASE='drop'")
        completed = subprocess.run(["bash", "-c", script], text=True, capture_output=True, check=False)
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout.strip(), "MYSQL_PROBE_FAILED=input")


class ProbeEvidenceTests(unittest.TestCase):
    def test_success_requires_expected_data_and_private_dns(self):
        self.assertTrue(probe.probe_result(result(), "read", PROBE_ID))
        for change in ({"phase": "write"}, {"probe": "other"}, {"row_count": 0}, {"private_dns": False}):
            with self.subTest(change=change), self.assertRaises(AssertionError):
                probe.probe_result(result(**change), "read", PROBE_ID)

    def test_running_command_is_not_a_pass(self):
        resource = result()
        resource["properties"]["instanceView"] = {}
        self.assertFalse(probe.probe_result(resource, "read", PROBE_ID))

    def test_failure_reports_only_the_failed_stage(self):
        failed = result(output="MYSQL_PROBE_FAILED=mysql-connect\n", state="Failed", code=1)
        with self.assertRaisesRegex(AssertionError, "stage=mysql-connect"):
            probe.probe_result(failed, "read", PROBE_ID)
        with self.assertRaisesRegex(AssertionError, "non-zero"):
            probe.probe_result(result(code=1), "read", PROBE_ID)

    def test_payloads_match_enriched_api_schemas(self):
        cases = (
            (mysql.MYSQL_PAYLOAD, "mysql", enrich_workspace_service_template),
            (mysql.VM_PAYLOAD, "guacamole/user_resources/guacamole-azure-linuxvm", enrich_user_resource_template),
        )
        for payload, folder, enrich in cases:
            with self.subTest(bundle=payload["templateName"]):
                schema = json.loads(
                    (ROOT / "templates/workspace_services" / folder / "template_schema.json").read_text()
                )
                validate(payload["properties"], enrich(SimpleNamespace(model_dump=lambda **_: schema)))

    def test_expected_skus_match_the_bundle(self):
        # Terraform uses a tier prefix, for example B_Standard_B2s. ARM returns the SKU name without it.
        locals_tf = (ROOT / "templates/workspace_services/mysql/terraform/locals.tf").read_text()
        for option, sku in mysql.SKUS.items():
            with self.subTest(option=option):
                self.assertRegex(locals_tf, rf'"{re.escape(option)}"\s*=\s*{{ value = "[A-Z]+_{sku}" }}')

    def test_deadline_precedes_container(self):
        jobs = yaml.safe_load((ROOT / ".github/workflows/deploy_tre_reusable.yml").read_text())["jobs"]
        job = jobs["e2e_tests_bundle"]
        reserve = next(s for s in job["steps"] if "MYSQL_VALIDATION_DEADLINE" in s.get("run", ""))
        run = next(s for s in job["steps"] if s["name"] == "Run E2E Tests")
        self.assertLess(job["steps"].index(reserve), job["steps"].index(run))
        self.assertEqual(reserve["if"], "inputs.e2eBundle == 'tre-workspace-service-mysql'")
        self.assertIn("MYSQL_VALIDATION_DEADLINE=${{ env.MYSQL_VALIDATION_DEADLINE }}", run["with"]["COMMAND"])


class ProbeRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_command_is_removed_and_never_counts_as_pass(self):
        failed = result(output="MYSQL_PROBE_FAILED=secret-access\n", state="Failed", code=1)
        arm = SimpleNamespace(request=AsyncMock(side_effect=[{}, failed]), delete=AsyncMock())
        with self.assertRaisesRegex(AssertionError, "secret-access"):
            await probe.run_probe(
                arm,
                VM_ID,
                "switzerlandnorth",
                server=VALUES["SERVER"],
                vault_name=VALUES["VAULT_NAME"],
                secret_name=VALUES["SECRET_NAME"],
                database="tredb",
                probe_id=PROBE_ID,
                phase="read",
            )
        command = arm.request.call_args_list[0].args[1]
        self.assertTrue(command.startswith(VM_ID + "/runCommands/mysql-probe-"))
        arm.delete.assert_awaited_once_with(command, probe.COMPUTE_API)
        body = arm.request.call_args_list[0].kwargs["body"]
        self.assertNotIn("parameters", body["properties"])
        self.assertNotIn("protectedParameters", body["properties"])

    async def test_prerequisite_context_exits_after_later_resources(self):
        events = []

        class Context:
            async def __aenter__(self):
                events.append("enter")

            async def __aexit__(self, *args):
                events.append(("exit", args))

        async def delete(*_, **__):
            events.append("delete")

        with (
            patch.dict(os.environ, MYSQL_VALIDATION_DEADLINE=""),
            patch.object(lifecycle, "post_resource", AsyncMock(return_value=("/mysql", "id"))),
            patch.object(lifecycle, "get_resource", AsyncMock(return_value={"operations": []})),
            patch.object(lifecycle, "disable_and_delete_resource", side_effect=delete),
        ):
            async with lifecycle.sql_lifecycle(True, deadline_variable="MYSQL_VALIDATION_DEADLINE") as owned:
                await owned.enter("Nexus", Context())
                await owned.create({}, "/services", "token")
        self.assertEqual(events, ["enter", "delete", ("exit", (None, None, None))])

    async def test_mysql_deadline_variable_is_read(self):
        with patch.dict(os.environ, MYSQL_VALIDATION_DEADLINE="nan"), self.assertRaisesRegex(ValueError, "finite"):
            lifecycle.lifecycle_deadlines("MYSQL_VALIDATION_DEADLINE")
