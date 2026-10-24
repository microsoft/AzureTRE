"""Check the health probe's evidence, role scope and cleanup boundaries."""

import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from jsonschema import validate
import yaml

from api_app.services.schema_service import enrich_user_resource_template, enrich_workspace_service_template
from e2e_tests import test_health as health
from e2e_tests.resources import health_probe as probe


ROOT = Path(__file__).resolve().parents[2]
GROUP = "/subscriptions/sub/resourceGroups/rg-tretest-ws-abcd"
VM_ID = f"{GROUP}/providers/Microsoft.Compute/virtualMachines/windowsvm1234"
FHIR_ID = f"{GROUP}/providers/Microsoft.HealthcareApis/workspaces/hsabcdsvc1234/fhirservices/fhirabcdsvc1234"
FHIR_URL = "https://hsabcdsvc1234-fhirabcdsvc1234.fhir.azurehealthcareapis.com"
PROBE_ID = "0123456789abcdef0123456789abcdef"


def result(evidence, state="Succeeded", code=0, output=None):
    return {
        "properties": {
            "provisioningState": "Succeeded",
            "instanceView": {
                "executionState": state,
                "exitCode": code,
                "output": output if output is not None else "HEALTH_PROBE_RESULT=" + json.dumps(evidence),
            },
        }
    }


class ProbeEvidenceTests(unittest.TestCase):
    def test_access_phase_requires_private_metadata_and_denied_requests(self):
        evidence = probe.expected_result("access", PROBE_ID, False)
        self.assertEqual(evidence["anonymous"], 401)
        self.assertEqual(evidence["unassigned"], 403)
        self.assertTrue(probe.probe_result(result(evidence), "access", PROBE_ID))
        for change in ({"anonymous": 200}, {"unassigned": 200}, {"private_dns": False}, {"fhir_version": "3.0.2"}):
            with self.subTest(change=change), self.assertRaises(AssertionError):
                probe.probe_result(result({**evidence, **change}), "access", PROBE_ID)

    def test_data_phases_require_the_written_row(self):
        for phase, dicom in (("write", False), ("read", True)):
            evidence = probe.expected_result(phase, PROBE_ID, dicom)
            with self.subTest(phase=phase):
                self.assertTrue(probe.probe_result(result(evidence), phase, PROBE_ID, dicom))
                with self.assertRaises(AssertionError):
                    probe.probe_result(result({**evidence, "count": 0}), phase, PROBE_ID, dicom)
        evidence = probe.expected_result("read", PROBE_ID, False)
        with self.assertRaises(AssertionError):
            probe.probe_result(result(evidence), "read", PROBE_ID, True)

    def test_running_command_is_not_a_pass_and_failure_names_the_stage(self):
        running = result({})
        running["properties"]["instanceView"] = {}
        self.assertFalse(probe.probe_result(running, "access", PROBE_ID))
        failed = result({}, state="Failed", code=1, output="HEALTH_PROBE_FAILED=fhir-role\n")
        with self.assertRaisesRegex(AssertionError, "stage=fhir-role"):
            probe.probe_result(failed, "write", PROBE_ID)

    def test_payloads_match_enriched_api_schemas(self):
        cases = (
            (health.HEALTH_PAYLOAD, "health-services", enrich_workspace_service_template),
            (health.VM_PAYLOAD, "guacamole/user_resources/guacamole-azure-windowsvm", enrich_user_resource_template),
        )
        for payload, folder, enrich in cases:
            with self.subTest(bundle=payload["templateName"]):
                schema = json.loads(
                    (ROOT / "templates/workspace_services" / folder / "template_schema.json").read_text()
                )
                validate(payload["properties"], enrich(SimpleNamespace(model_dump=lambda **_: schema)))
        self.assertFalse(any(v for k, v in health.VM_PAYLOAD["properties"].items() if k.startswith("install_")))

    def test_deadline_precedes_container(self):
        jobs = yaml.safe_load((ROOT / ".github/workflows/deploy_tre_reusable.yml").read_text())["jobs"]
        job = jobs["e2e_tests_bundle"]
        reserve = next(s for s in job["steps"] if "HEALTH_VALIDATION_DEADLINE" in s.get("run", ""))
        run = next(s for s in job["steps"] if s["name"] == "Run E2E Tests")
        self.assertLess(job["steps"].index(reserve), job["steps"].index(run))
        self.assertEqual(reserve["if"], "inputs.e2eBundle == 'tre-workspace-service-health'")
        self.assertIn("HEALTH_VALIDATION_DEADLINE=${{ env.HEALTH_VALIDATION_DEADLINE }}", run["with"]["COMMAND"])


class ProbeRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_role_is_scoped_to_one_service_and_removed_after_failure(self):
        arm = SimpleNamespace(request=AsyncMock(return_value={}), delete=AsyncMock())
        with self.assertRaisesRegex(RuntimeError, "write failed"):
            async with probe.role_access(arm, FHIR_ID, probe.FHIR_DATA_CONTRIBUTOR, "principal", "sub"):
                raise RuntimeError("write failed")
        assignment = arm.request.call_args.args[1]
        self.assertTrue(assignment.startswith(FHIR_ID + "/providers/Microsoft.Authorization/roleAssignments/"))
        body = arm.request.call_args.kwargs["body"]["properties"]
        self.assertEqual(body["principalId"], "principal")
        self.assertTrue(body["roleDefinitionId"].endswith("/roleDefinitions/" + probe.FHIR_DATA_CONTRIBUTOR))
        arm.delete.assert_awaited_once_with(assignment, probe.ROLE_API)

    async def test_failed_command_is_removed_and_dicom_is_optional(self):
        failed = result({}, state="Failed", code=1, output="HEALTH_PROBE_FAILED=fhir-metadata\n")
        for dicom_url in ("", "https://hsabcdsvc1234-dicomabcdsvc1234.dicom.azurehealthcareapis.com"):
            arm = SimpleNamespace(request=AsyncMock(side_effect=[{}, failed]), delete=AsyncMock())
            with self.subTest(dicom_url=dicom_url), self.assertRaisesRegex(AssertionError, "fhir-metadata"):
                await probe.run_probe(
                    arm,
                    VM_ID,
                    "switzerlandnorth",
                    fhir_url=FHIR_URL,
                    probe_id=PROBE_ID,
                    phase="read",
                    dicom_url=dicom_url,
                )
            command = arm.request.call_args_list[0].args[1]
            self.assertTrue(command.startswith(VM_ID + "/runCommands/health-probe-"))
            arm.delete.assert_awaited_once_with(command, probe.COMPUTE_API)
            names = [p["name"] for p in arm.request.call_args_list[0].kwargs["body"]["properties"]["parameters"]]
            self.assertEqual(names, ["FhirUrl", "ProbeId", "Phase"] + (["DicomUrl"] if dicom_url else []))

    async def test_only_a_dns_failure_is_tried_again(self):
        def failed(stage):
            return result({}, state="Failed", code=1, output=f"HEALTH_PROBE_FAILED={stage}\n")

        passed = result(probe.expected_result("access", PROBE_ID, False))
        cases = (
            ([failed("private-dns"), passed], None),
            ([failed("private-dns")] * probe.DNS_ATTEMPTS, "stage=private-dns"),
            ([failed("fhir-metadata")], "stage=fhir-metadata"),
        )
        for results, error in cases:
            # Each attempt creates a command, reads its result and then removes the command.
            responses = [response for r in results for response in ({}, r)]
            arm = SimpleNamespace(request=AsyncMock(side_effect=responses), delete=AsyncMock())
            with self.subTest(error=error), patch.object(probe, "DNS_RETRY_SECONDS", 0):
                run = probe.run_probe(
                    arm, VM_ID, "switzerlandnorth", fhir_url=FHIR_URL, probe_id=PROBE_ID, phase="access"
                )
                if error:
                    with self.assertRaisesRegex(AssertionError, error):
                        await run
                else:
                    await run
                self.assertEqual(arm.delete.await_count, len(results))

    async def test_public_requests_are_sent_again_until_azure_blocks_them(self):
        urls = {"fhir": FHIR_URL + "/metadata", "dicom": "https://dicom.example/health/check"}
        cases = (
            ([200, 403, 403, 403], {}, {"fhir": 403, "dicom": 403}),
            # If the wait ends first, the caller gets the last statuses and reports them.
            ([200, 401], {"PUBLIC_WAIT_SECONDS": 0}, {"fhir": 200, "dicom": 401}),
        )
        for codes, settings, expected in cases:
            responses = iter(codes)
            transport = httpx.MockTransport(lambda request: httpx.Response(next(responses)))
            with self.subTest(codes=codes), patch.multiple(probe, PUBLIC_RETRY_SECONDS=0, **settings):
                async with httpx.AsyncClient(transport=transport) as client:
                    statuses = await probe.public_statuses(client, urls)
                self.assertEqual(statuses, expected)
