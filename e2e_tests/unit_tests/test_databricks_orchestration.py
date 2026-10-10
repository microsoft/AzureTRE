"""Check Databricks preflight and owned dependency ordering without Azure."""

from contextlib import asynccontextmanager
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import yaml

from e2e_tests import test_databricks as case
from e2e_tests.bundle_evidence import BundleReport, activate

AUTH_ID = "11111111-1111-4111-8111-111111111111"
WORKSPACE_ID = "22222222-2222-4222-8222-222222222222"
SERVICE_ID = "33333333-3333-4333-8333-333333333333"


class DatabricksPreflightTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.object(case, "get_admin_token", AsyncMock(return_value="admin")))
        self.read = self.enterContext(patch.object(case, "get_resource", AsyncMock()))

    async def test_existing_workspace_blocks_before_reading_shared_services(self):
        self.read.return_value = {"workspaces": [{"id": WORKSPACE_ID}]}
        with self.assertRaisesRegex(RuntimeError, "no existing TRE workspaces"):
            await case.require_isolation(True)
        self.read.assert_awaited_once()

    async def test_failed_or_disabled_auth_is_not_adopted(self):
        self.read.side_effect = [
            {"workspaces": []},
            {
                "sharedServices": [
                    {
                        "id": AUTH_ID,
                        "templateName": case.AUTH,
                        "isEnabled": False,
                        "deploymentStatus": "deployment_failed",
                    }
                ]
            },
        ]
        with self.assertRaisesRegex(RuntimeError, "existing Databricks"):
            await case.require_isolation(True)

    async def test_cleanup_guard_rejects_a_second_auth_service(self):
        self.read.side_effect = [
            {"workspaces": []},
            {
                "sharedServices": [
                    {"id": AUTH_ID, "templateName": case.AUTH},
                    {"id": SERVICE_ID, "templateName": case.AUTH},
                ]
            },
        ]
        with self.assertRaisesRegex(RuntimeError, "existing Databricks"):
            await case.require_isolation(True, AUTH_ID)

    async def test_cleanup_guard_accepts_only_owned_auth(self):
        auth = {"id": AUTH_ID, "templateName": case.AUTH}
        self.read.side_effect = [{"workspaces": []}, {"sharedServices": [auth]}]
        self.assertEqual(await case.require_isolation(True, AUTH_ID), [auth])

    async def test_wrong_registered_version_fails(self):
        self.read.return_value = {"name": case.AUTH, "version": "0.0.0"}
        with self.assertRaisesRegex(ValueError, "Register the checkout version"):
            await case.require_templates(True, False)

    async def test_missing_disabled_duplicate_or_old_firewall_fails(self):
        template = case.strings.FIREWALL_SHARED_SERVICE
        fw = {
            "id": "firewall",
            "templateName": template,
            "isEnabled": True,
            "deploymentStatus": "deployed",
            "templateVersion": case.load_catalog()[template]["source_version"],
        }
        for records in ([], [fw, fw], [dict(fw, isEnabled=False)], [dict(fw, templateVersion="old")]):
            with self.subTest(records=records), self.assertRaises(ValueError):
                case.require_firewall(records)

    def test_existing_firewall_is_reported_only_as_a_reused_prerequisite(self):
        directory = self.enterContext(TemporaryDirectory())
        filename = Path(directory) / "evidence.json"
        activate(BundleReport(filename, {}))
        self.addCleanup(activate, None)
        template = case.strings.FIREWALL_SHARED_SERVICE
        identity = {
            "id": "firewall",
            "templateName": template,
            "templateVersion": case.load_catalog()[template]["source_version"],
        }
        firewall = dict(identity, isEnabled=True, deploymentStatus="deployed", properties={"secret": "do-not-copy"})

        for _ in range(2):
            self.assertEqual(case.require_firewall([firewall]), identity["id"])

        report = json.loads(filename.read_text())
        self.assertEqual(report["reused_resources"], [identity])
        self.assertEqual(report["resources"], [])
        self.assertNotIn("do-not-copy", filename.read_text())


class DatabricksOrchestrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.created = []
        self.callbacks = []
        self.settings = SimpleNamespace(subscription="subscription", tre_id="tre-test", tenant="tenant")
        self.enterContext(patch.object(case, "require_settings", return_value=self.settings))
        self.templates = self.enterContext(patch.object(case, "require_templates", AsyncMock()))
        self.isolation = self.enterContext(patch.object(case, "require_isolation", AsyncMock(return_value=[])))
        self.preflight = self.enterContext(patch.object(case, "preflight", AsyncMock(return_value="switzerlandnorth")))
        self.firewall = self.enterContext(patch.object(case, "require_firewall", return_value="firewall"))
        self.validate = self.enterContext(patch.object(case, "validate_resources", AsyncMock()))
        self.enterContext(patch.object(case, "auth_ids", return_value={"kind": "auth"}))
        self.enterContext(patch.object(case, "service_ids", return_value={"kind": "service"}))
        self.remove = self.enterContext(patch.object(case, "assert_removed", AsyncMock()))
        self.dns = self.enterContext(patch.object(case, "assert_auth_dns_empty", AsyncMock()))
        self.enterContext(patch.object(case.config, "TEST_WORKSPACE_ID", "unrelated-workspace"))
        self.enterContext(patch.object(case.config, "TEST_WORKSPACE_APP_PLAN", ""))

        async def create(payload, endpoint, workspace_id=None, **kwargs):
            self.created.append((payload, endpoint, workspace_id))
            self.callbacks.append(kwargs)
            if payload["templateName"] == case.AUTH:
                return "/shared-services/" + AUTH_ID, AUTH_ID
            if payload["templateName"] == case.strings.BASE_WORKSPACE:
                self.assertEqual(payload["properties"]["auth_type"], "Automatic")
                self.assertFalse(payload["properties"]["enable_backup"])
                return "/workspaces/" + WORKSPACE_ID, WORKSPACE_ID
            self.assertEqual(workspace_id, WORKSPACE_ID)
            self.assertNotIn("address_space", payload["properties"])
            self.assertIs(payload["properties"]["is_exposed_externally"], False)
            return f"/workspaces/{WORKSPACE_ID}/workspace-services/{SERVICE_ID}", SERVICE_ID

        @asynccontextmanager
        async def lifecycle(_):
            yield SimpleNamespace(create=create)

        @asynccontextmanager
        async def arm():
            yield "arm-client"

        self.enterContext(patch.object(case, "databricks_lifecycle", lifecycle))
        self.enterContext(patch.object(case, "arm_client", arm))
        self.enterContext(
            patch.object(
                case,
                "deployed",
                AsyncMock(return_value={"properties": {"auth_type": "Automatic", "is_exposed_externally": False}}),
            )
        )

    async def test_auth_only_creates_no_workspace_and_protects_cleanup(self):
        await case.validate_lifecycle(True, workspace_service=False)
        self.assertEqual([p["templateName"] for p, _, _ in self.created], [case.AUTH])
        self.firewall.assert_not_called()
        self.assertTrue(self.callbacks[0]["protected"])
        await self.callbacks[0]["before_remove"]("/shared-services/" + AUTH_ID, AUTH_ID)
        self.isolation.assert_awaited_with(True, AUTH_ID)
        await self.callbacks[0]["after_remove"]("/shared-services/" + AUTH_ID, AUTH_ID)
        self.remove.assert_awaited_once_with("arm-client", {"kind": "auth"})
        self.dns.assert_awaited_once_with("arm-client", self.settings)

    async def test_service_creates_auth_then_owned_workspace_then_service(self):
        await case.validate_lifecycle(True, workspace_service=True)
        self.assertEqual(
            [p["templateName"] for p, _, _ in self.created], [case.AUTH, case.strings.BASE_WORKSPACE, case.SERVICE]
        )
        self.preflight.assert_awaited_once_with("arm-client", self.settings, workspace_service=True)
        self.assertEqual(self.validate.await_count, 2)
        self.assertTrue(all("after_remove" in callback for callback in self.callbacks))

    async def test_every_preflight_failure_prevents_all_creation(self):
        for mock in (self.templates, self.isolation, self.preflight):
            with self.subTest(check=mock):
                mock.side_effect = ValueError("unsafe prerequisite")
                with self.assertRaisesRegex(ValueError, "unsafe prerequisite"):
                    await case.validate_lifecycle(True, workspace_service=True)
                self.assertEqual(self.created, [])
                mock.side_effect = None

    async def test_bad_firewall_prevents_auth_creation(self):
        self.firewall.side_effect = ValueError("firewall unavailable")
        with self.assertRaisesRegex(ValueError, "firewall unavailable"):
            await case.validate_lifecycle(True, workspace_service=True)
        self.preflight.assert_not_awaited()
        self.assertEqual(self.created, [])


class DatabricksWorkflowTests(unittest.TestCase):
    def test_bundle_job_reserves_cleanup_before_setup_and_forwards_deadline(self):
        root = Path(__file__).resolve().parents[2]
        workflow = yaml.safe_load((root / ".github/workflows/deploy_tre_reusable.yml").read_text())
        job = workflow["jobs"]["e2e_tests_bundle"]
        self.assertIn("e2e_tests_smoke", job["needs"])
        step = next(s for s in job["steps"] if s["name"] == "Reserve Databricks cleanup and reporting time")
        self.assertLess(
            job["steps"].index(step), next(i for i, s in enumerate(job["steps"]) if s["name"] == "Checkout")
        )
        self.assertIn(case.AUTH, step["if"])
        self.assertIn(case.SERVICE, step["if"])
        self.assertIn("270 * 60", step["run"])
        self.assertGreater(job["timeout-minutes"], 270)
        command = next(s for s in job["steps"] if s["name"] == "Run E2E Tests")["with"]["COMMAND"]
        self.assertIn("DATABRICKS_VALIDATION_DEADLINE=${{ env.DATABRICKS_VALIDATION_DEADLINE }}", command)
        self.assertNotIn("databricks_validation", workflow["jobs"]["e2e_tests_custom"].get("if", ""))
