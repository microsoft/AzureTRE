"""Check AML prerequisite failures and reject unsafe deployed configurations."""

import asyncio
from copy import deepcopy
import os
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

import yaml

from e2e_tests.resources import aml

SUBSCRIPTION = "11111111-1111-4111-8111-111111111111"
TENANT = "22222222-2222-4222-8222-222222222222"
USER = "33333333-3333-4333-8333-333333333333"
WORKSPACE = "44444444-4444-4444-8444-444444444444"
SERVICE = "55555555-5555-4555-8555-555555555555"
RESOURCE = "66666666-6666-4666-8666-666666666666"
ROOT = Path(__file__).resolve().parents[2]


class PrerequisiteTests(unittest.TestCase):
    def setUp(self):
        self.environment = self.enterContext(
            patch.dict(
                os.environ,
                {
                    "ARM_SUBSCRIPTION_ID": SUBSCRIPTION,
                    "ARM_TENANT_ID": TENANT,
                    "AZURE_ENVIRONMENT": "AzureCloud",
                    "TEST_AML_USER_OBJECT_ID": USER,
                },
                clear=True,
            )
        )
        self.enterContext(patch.object(aml.config, "AAD_TENANT_ID", TENANT))
        self.enterContext(patch.object(aml.config, "TRE_ID", "tre-test"))

    def test_matching_tenants_and_explicit_user(self):
        self.assertEqual(aml.require_prerequisites(compute=True), (SUBSCRIPTION, TENANT, USER))

    def test_parent_does_not_require_a_compute_owner(self):
        os.environ.pop("TEST_AML_USER_OBJECT_ID")
        self.assertEqual(aml.require_prerequisites(), (SUBSCRIPTION, TENANT, ""))

    def test_missing_nil_or_path_like_user_is_rejected(self):
        for value in ("", "00000000-0000-0000-0000-000000000000", USER + "/users", "$(id)"):
            with self.subTest(value=value), patch.dict(os.environ, TEST_AML_USER_OBJECT_ID=value):
                with self.assertRaisesRegex(ValueError, "TEST_AML_USER_OBJECT_ID"):
                    aml.require_prerequisites(compute=True)

    def test_cross_tenant_assignment_is_rejected(self):
        with patch.object(aml.config, "AAD_TENANT_ID", USER):
            with self.assertRaisesRegex(ValueError, "tenants to match"):
                aml.require_prerequisites(compute=True)

    def test_other_cloud_is_rejected(self):
        with patch.dict(os.environ, AZURE_ENVIRONMENT="AzureUSGovernment"):
            with self.assertRaisesRegex(ValueError, "AzureCloud"):
                aml.require_prerequisites()

    def test_names_match_the_bundle_contract_and_reject_path_injection(self):
        group, parent, subnet, compute = aml.resource_ids(SUBSCRIPTION, "tre-test", WORKSPACE, SERVICE, RESOURCE)
        self.assertTrue(group.endswith("/resourceGroups/rg-tre-test-ws-4444"))
        self.assertTrue(parent.endswith("/workspaces/ml-tre-test-ws-4444-svc-5555"))
        self.assertTrue(subnet.endswith("/virtualNetworks/vnet-tre-test-ws-4444/subnets/AMLSubnet5555"))
        self.assertEqual(compute, parent + "/computes/ci-55556666")
        with self.assertRaises(ValueError):
            aml.resource_ids(SUBSCRIPTION, "tre-test/other", WORKSPACE, SERVICE, RESOURCE)


class ComputeConfigurationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        _, self.parent, self.subnet, self.compute = aml.resource_ids(
            SUBSCRIPTION, "tre-test", WORKSPACE, SERVICE, RESOURCE
        )
        self.tags = {
            "tre_id": "tre-test",
            "tre_workspace_id": WORKSPACE,
            "tre_workspace_service_id": SERVICE,
            "tre_user_resource_id": RESOURCE,
        }
        self.resource = {
            "id": self.compute,
            "tags": self.tags.copy(),
            "properties": {
                "computeType": "ComputeInstance",
                "provisioningState": "Succeeded",
                "properties": {
                    "vmSize": "STANDARD_D2_V3",
                    "enableNodePublicIp": False,
                    "subnet": {"id": self.subnet},
                    "computeInstanceAuthorizationType": "personal",
                    "state": "Running",
                    "personalComputeInstanceSettings": {"assignedUser": {"objectId": USER, "tenantId": TENANT}},
                },
            },
        }

    def validate(self, resource):
        return aml.validate_compute(resource, self.compute, self.subnet, self.tags, TENANT, USER)

    async def test_waits_for_running_then_returns_verified_compute(self):
        starting = deepcopy(self.resource)
        starting["properties"]["properties"]["state"] = "Starting"
        arm = AsyncMock()
        arm.request.side_effect = [starting, self.resource]
        with patch.object(aml.asyncio, "sleep", new_callable=AsyncMock) as sleep:
            self.assertEqual(
                await aml.wait_for_compute(arm, self.compute, self.subnet, self.tags, TENANT, USER), self.resource
            )
            sleep.assert_awaited_once()

    def test_rejects_different_user_tenant_subnet_public_ip_and_size(self):
        changes = {
            "vmSize": "Standard_D16_v3",
            "enableNodePublicIp": True,
            "subnet": {"id": self.subnet + "-other"},
            "computeInstanceAuthorizationType": "shared",
            "connectivityEndpoints": {"publicIpAddress": "203.0.113.1"},
            "personalComputeInstanceSettings": {"assignedUser": {"objectId": TENANT, "tenantId": USER}},
        }
        for key, value in changes.items():
            with self.subTest(field=key):
                resource = deepcopy(self.resource)
                resource["properties"]["properties"][key] = value
                with self.assertRaises(AssertionError):
                    self.validate(resource)

    def test_rejects_wrong_resource_or_missing_ownership_tag(self):
        for key in self.tags:
            resource = deepcopy(self.resource)
            resource["tags"].pop(key)
            with self.subTest(key=key), self.assertRaisesRegex(AssertionError, "ownership tags"):
                self.validate(resource)
        resource = deepcopy(self.resource)
        resource["id"] += "-other"
        with self.assertRaisesRegex(AssertionError, "test-created"):
            self.validate(resource)

    def test_terminal_compute_failures_do_not_keep_polling(self):
        for state in ("Unusable", "CreateFailed", "SetupFailed", "UserSetupFailed"):
            with self.subTest(state=state):
                resource = deepcopy(self.resource)
                resource["properties"]["properties"]["state"] = state
                with self.assertRaisesRegex(AssertionError, "compute failed"):
                    self.validate(resource)

    async def test_arm_errors_are_not_treated_as_removal(self):
        arm = AsyncMock()
        arm.request.side_effect = RuntimeError("ARM HTTP 403")
        with self.assertRaisesRegex(RuntimeError, "403"):
            await aml.assert_removed(arm, self.compute)

    async def test_removal_waits_for_absence(self):
        arm = AsyncMock()
        arm.request.side_effect = [self.resource, None]
        with patch.object(aml.asyncio, "sleep", new_callable=AsyncMock) as sleep:
            await aml.assert_removed(arm, self.compute)
            sleep.assert_awaited_once()

    async def test_transitional_compute_does_not_wait_without_a_deadline(self):
        arm = AsyncMock()
        arm.request.return_value = deepcopy(self.resource)
        arm.request.return_value["properties"]["properties"]["state"] = "Creating"
        real_timeout = asyncio.timeout
        with patch.object(aml.asyncio, "timeout", side_effect=lambda _: real_timeout(0.01)):
            with self.assertRaises(TimeoutError):
                await aml.wait_for_compute(arm, self.compute, self.subnet, self.tags, TENANT, USER)

    def test_parent_must_be_private_and_owned(self):
        parent = {
            "id": self.parent,
            "tags": self.tags,
            "properties": {"provisioningState": "Succeeded", "publicNetworkAccess": "Disabled"},
        }
        aml.validate_service(parent, self.parent, self.tags)
        parent["properties"]["publicNetworkAccess"] = "Enabled"
        with self.assertRaisesRegex(AssertionError, "public access"):
            aml.validate_service(parent, self.parent, self.tags)


class WorkflowPrerequisiteTests(unittest.TestCase):
    def test_compute_is_published_and_registered_after_its_parent(self):
        jobs = yaml.safe_load((ROOT / ".github/workflows/deploy_tre_reusable.yml").read_text())["jobs"]
        directory = "./templates/workspace_services/azureml/user_resources/aml_compute"
        published = jobs["publish_bundles"]["strategy"]["matrix"]["include"]
        registered = jobs["register_user_resource_bundles"]["strategy"]["matrix"]["include"]
        self.assertEqual(
            [entry["BUNDLE_TYPE"] for entry in published if entry["BUNDLE_DIR"] == directory], ["user_resource"]
        )
        self.assertEqual(
            [entry["WORKSPACE_SERVICE_NAME"] for entry in registered if entry["BUNDLE_DIR"] == directory],
            ["tre-service-azureml"],
        )
        self.assertIn("register_bundles", jobs["register_user_resource_bundles"]["needs"])

    def test_owner_is_passed_as_environment_data_and_deadline_starts_before_container(self):
        action = yaml.safe_load((ROOT / ".github/actions/devcontainer_run_command/action.yml").read_text())
        step = next(s for s in action["runs"]["steps"] if s["name"] == "Run command in DevContainer")
        self.assertEqual(step["env"]["TEST_AML_USER_OBJECT_ID"], "${{ inputs.TEST_AML_USER_OBJECT_ID }}")
        self.assertIn("-e TEST_AML_USER_OBJECT_ID", step["run"])
        self.assertNotIn("${{ inputs.TEST_AML_USER_OBJECT_ID }}", step["run"])
        jobs = yaml.safe_load((ROOT / ".github/workflows/deploy_tre_reusable.yml").read_text())["jobs"]
        steps = jobs["e2e_tests_bundle"]["steps"]
        self.assertIn("AML_VALIDATION_DEADLINE", steps[0]["run"])
        run = next(s for s in steps if s["name"] == "Run E2E Tests")
        self.assertIn("AML_VALIDATION_DEADLINE=${{ env.AML_VALIDATION_DEADLINE }}", run["with"]["COMMAND"])
        self.assertEqual(run["with"]["TEST_AML_USER_OBJECT_ID"], "${{ vars.TEST_AML_USER_OBJECT_ID }}")
