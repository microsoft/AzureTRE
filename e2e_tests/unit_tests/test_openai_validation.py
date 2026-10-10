"""Check OpenAI prerequisite failures, evidence and owned-resource cleanup offline."""

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from httpx import AsyncClient, MockTransport, Response
from jsonschema import validate
import yaml

from e2e_tests import test_openai as lifecycle
from e2e_tests.resources import openai, resource
from e2e_tests.resources.sql_probe import ArmClient

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]
SUBSCRIPTION = "00000000-0000-4000-8000-000000000000"
WORKSPACE = "11111111-1111-4111-8111-111111111111"
SERVICE = "22222222-2222-4222-8222-222222222222"
PATH = f"/workspaces/{WORKSPACE}/workspace-services/{SERVICE}"
GROUP = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/rg-tretest-ws-1111"
ACCOUNT = GROUP + "/providers/Microsoft.CognitiveServices/accounts/openai-tretest-ws-1111-svc-2222"
DEPLOYMENT = "openai-gpt-5.1-2025-11-13-tretest-ws-1111-svc-2222"


def model_entry():
    return {
        "kind": "OpenAI",
        "skuName": "S0",
        "model": {
            "format": "OpenAI",
            "name": "gpt-5.1",
            "version": "2025-11-13",
            "lifecycleStatus": "GenerallyAvailable",
            "capabilities": {"chatCompletion": "true"},
            "skus": [{"name": "Standard", "usageName": "OpenAI.Standard.gpt-5.1"}],
        },
    }


def usage_entry():
    return {"name": {"value": "OpenAI.Standard.gpt-5.1"}, "currentValue": 9, "limit": 10, "unit": "Count"}


class ModelPrerequisiteTests(unittest.TestCase):
    def test_current_exact_model_and_last_capacity_unit_are_accepted(self):
        sku = openai.supported_sku([model_entry()], NOW)
        openai.check_capacity(sku, [usage_entry()])

    def test_wrong_version_preview_and_non_chat_models_are_rejected(self):
        for field, value in (
            ("version", "wrong"),
            ("lifecycleStatus", "Preview"),
            ("capabilities", {}),
            ("format", "other"),
        ):
            entry = model_entry()
            entry["model"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "no current regional"):
                openai.supported_sku([entry], NOW)

    def test_global_fine_tuning_and_expired_standard_tiers_are_rejected(self):
        cases = (
            ("name", "GlobalStandard"),
            ("usageName", "OpenAI.Standard.gpt-5.1-finetune"),
            ("usageName", ""),
            ("deprecationDate", "2026-10-10T00:00:00Z"),
            ("deprecationDate", "invalid"),
            ("deprecationDate", "2027-01-01"),
        )
        for key, value in cases:
            entry = model_entry()
            entry["model"]["skus"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                openai.supported_sku([entry], NOW)
        entry = model_entry()
        entry["model"]["deprecation"] = {"inference": "2020-01-01T00:00:00Z"}
        with self.assertRaises(ValueError):
            openai.supported_sku([entry], NOW)

    def test_missing_exhausted_and_invalid_quota_never_pass(self):
        sku = openai.supported_sku([model_entry()], NOW)
        cases = [[], [dict(usage_entry(), name={"value": "GlobalStandard"})]]
        for key, value in (
            ("currentValue", 10),
            ("currentValue", -1),
            ("limit", None),
            ("limit", float("nan")),
            ("limit", True),
            ("status", "Blocked"),
            ("status", "Unknown"),
        ):
            cases.append([dict(usage_entry(), **{key: value})])
        for usages in cases:
            with self.subTest(usages=usages), self.assertRaises(ValueError):
                openai.check_capacity(sku, usages)

    def test_model_capacity_minimum_and_step_can_prevent_deployment(self):
        for capacity in ({"minimum": 10}, {"allowedValues": [2, 4]}, {"step": 0}, {"minimum": 0, "step": 2}):
            sku = dict(openai.supported_sku([model_entry()], NOW), capacity=capacity)
            with self.subTest(capacity=capacity), self.assertRaisesRegex(ValueError, "capacity unit"):
                openai.check_capacity(sku, [usage_entry()])

    def test_bundle_schema_and_ci_registration_agree_with_selection(self):
        folder = ROOT / "templates/workspace_services/openai"
        schema = json.loads((folder / "template_schema.json").read_text())
        validate({"openai_model": openai.MODEL, "is_exposed_externally": False}, schema)
        self.assertEqual(schema["properties"]["openai_model"]["default"], openai.MODEL)
        manifest = yaml.safe_load((folder / "porter.yaml").read_text())
        self.assertEqual(manifest["version"], "1.1.0")
        workflow = yaml.safe_load((ROOT / ".github/workflows/deploy_tre_reusable.yml").read_text())
        registrations = workflow["jobs"]["register_bundles"]["strategy"]["matrix"]["include"]
        self.assertIn(
            {"BUNDLE_TYPE": "workspace_service", "BUNDLE_DIR": "./templates/workspace_services/openai"}, registrations
        )


class PaginationTests(unittest.IsolatedAsyncioTestCase):
    async def test_pagination_retains_api_version_and_renews_credentials(self):
        collection = f"/subscriptions/{SUBSCRIPTION}/providers/Microsoft.CognitiveServices/locations/westeurope/models"
        requests = []

        def handle(request):
            requests.append(request)
            self.assertEqual(request.url.params["api-version"], openai.COGNITIVE_API)
            self.assertEqual(request.headers["Authorization"], "Bearer token")
            if len(requests) == 1:
                return Response(
                    200,
                    json={
                        "value": [1],
                        "nextLink": f"https://management.azure.com{collection}?api-version={openai.COGNITIVE_API}&$skiptoken=a%2Bb",
                    },
                )
            self.assertEqual(request.url.params["$skiptoken"], "a+b")
            return Response(200, json={"value": [2]})

        credential = Mock()
        credential.get_token.return_value = SimpleNamespace(token="token")
        async with AsyncClient(transport=MockTransport(handle)) as client:
            self.assertEqual(await openai.list_values(ArmClient(client, credential), collection), [1, 2])
        self.assertEqual(credential.get_token.call_count, 2)

    async def test_cross_host_path_and_version_links_fail_before_next_request(self):
        collection = f"/subscriptions/{SUBSCRIPTION}/models"
        for link in (
            "https://example.test" + collection + "?api-version=" + openai.COGNITIVE_API,
            "https://management.azure.com/another?api-version=" + openai.COGNITIVE_API,
            "https://management.azure.com" + collection + "?api-version=wrong",
        ):
            arm = SimpleNamespace(request=AsyncMock(return_value={"value": [], "nextLink": link}))
            with self.subTest(link=link), self.assertRaises(ValueError):
                await openai.list_values(arm, collection)
            self.assertEqual(arm.request.await_count, 1)

    async def test_repeated_continuation_is_rejected(self):
        collection = f"/subscriptions/{SUBSCRIPTION}/models"
        arm = SimpleNamespace(
            request=AsyncMock(
                return_value={
                    "value": [],
                    "nextLink": f"https://management.azure.com{collection}?api-version={openai.COGNITIVE_API}&$skiptoken=same",
                }
            )
        )
        with self.assertRaises(ValueError):
            await openai.list_values(arm, collection)
        self.assertEqual(arm.request.await_count, 2)


class OpenAILifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(
            patch.dict(os.environ, {"ARM_SUBSCRIPTION_ID": SUBSCRIPTION, "AZURE_ENVIRONMENT": "AzureCloud"})
        )
        self.enterContext(patch.object(lifecycle.config, "TRE_ID", "tretest"))
        self.enterContext(patch.object(lifecycle, "get_workspace_owner_token", AsyncMock(return_value="token")))
        self.preflight = self.enterContext(patch.object(lifecycle, "check_prerequisites", AsyncMock()))
        self.post = self.enterContext(patch.object(resource, "post_resource", AsyncMock(return_value=(PATH, SERVICE))))
        self.cleanup = self.enterContext(patch.object(resource, "disable_and_delete_resource", AsyncMock()))
        self.lookup_status = 404
        self.workspace = {"workspace": {"properties": {}}}
        self.service = {
            "workspaceService": {
                "id": SERVICE,
                "templateName": "tre-workspace-service-openai",
                "deploymentStatus": "deployed",
                "properties": {
                    "openai_model": openai.MODEL,
                    "is_exposed_externally": False,
                    "openai_fqdn": "https://openai.example.test/",
                    "openai_deployment_id": DEPLOYMENT,
                },
            }
        }
        self.get = self.enterContext(
            patch.object(
                lifecycle,
                "get_resource",
                AsyncMock(
                    side_effect=lambda endpoint, *_: deepcopy(
                        self.service if "workspace-services" in endpoint else self.workspace
                    )
                ),
            )
        )
        self.account = {
            "properties": {
                "provisioningState": "Succeeded",
                "publicNetworkAccess": "Disabled",
                "endpoint": "https://openai.example.test/",
            }
        }
        self.deployment = {
            "properties": {
                "provisioningState": "Succeeded",
                "model": {"format": "OpenAI", "name": "gpt-5.1", "version": "2025-11-13"},
            },
            "sku": {"name": "Standard", "capacity": 1},
        }
        self.retained = False
        self.group = GROUP
        self.account_id = ACCOUNT
        self.deployment_name = DEPLOYMENT

        async def request(method, identifier, api, **kwargs):
            self.assertEqual(method, "GET")
            if identifier == self.group:
                return {"location": "westeurope"}
            if identifier == self.account_id:
                return self.account if not kwargs.get("missing_ok") or self.retained else None
            if identifier == self.account_id + "/deployments/" + self.deployment_name:
                return self.deployment
            raise AssertionError("Unexpected ARM resource")

        self.arm = SimpleNamespace(request=AsyncMock(side_effect=request))

        @asynccontextmanager
        async def arm():
            yield self.arm

        self.enterContext(patch.object(lifecycle, "arm_client", arm))

        def lookup(request):
            self.assertEqual(request.url.path, "/api" + PATH)
            return Response(self.lookup_status)

        self.enterContext(
            patch.object(lifecycle, "AsyncClient", lambda **_: AsyncClient(transport=MockTransport(lookup)))
        )
        self.enterContext(
            patch.object(lifecycle, "get_full_endpoint", lambda endpoint: "https://tre.example.test" + endpoint)
        )

    async def run_case(self):
        await lifecycle.test_private_openai_lifecycle(True, (f"/workspaces/{WORKSPACE}", WORKSPACE))

    async def test_success_checks_actual_region_and_removes_only_the_created_service(self):
        await self.run_case()
        self.preflight.assert_awaited_once_with(self.arm, SUBSCRIPTION, "westeurope")
        self.assertTrue(self.post.await_args.kwargs["cleanup_failed_create"])
        payload = self.post.await_args.args[0]
        self.assertEqual(payload["properties"]["openai_model"], openai.MODEL)
        self.assertIs(payload["properties"]["is_exposed_externally"], False)
        self.cleanup.assert_awaited_once_with("/api" + PATH, "token", True)

    async def test_hyphenated_tre_id_reaches_validation_and_cleanup(self):
        self.group = GROUP.replace("tretest", "tre-test")
        self.account_id = ACCOUNT.replace("tretest", "tre-test")
        self.deployment_name = DEPLOYMENT.replace("tretest", "tre-test")
        self.service["workspaceService"]["properties"]["openai_deployment_id"] = self.deployment_name
        with patch.object(lifecycle.config, "TRE_ID", "tre-test"):
            await self.run_case()
        self.preflight.assert_awaited_once_with(self.arm, SUBSCRIPTION, "westeurope")
        self.post.assert_awaited_once()
        self.cleanup.assert_awaited_once_with("/api" + PATH, "token", True)

    async def test_path_and_query_characters_are_rejected_before_arm_access(self):
        for tre_id in ("tre/test", "tre?test", "tre#test", "tre%2ftest"):
            with self.subTest(tre_id=tre_id), patch.object(lifecycle.config, "TRE_ID", tre_id):
                with self.assertRaisesRegex(ValueError, "Invalid subscription or TRE identifier"):
                    await self.run_case()
        self.arm.request.assert_not_awaited()
        self.post.assert_not_awaited()

    async def test_model_or_quota_failure_prevents_service_creation(self):
        self.preflight.side_effect = ValueError("quota unavailable")
        with self.assertRaisesRegex(ValueError, "quota unavailable"):
            await self.run_case()
        self.post.assert_not_awaited()
        self.cleanup.assert_not_awaited()

    async def test_other_subscription_fails_before_arm_access_or_service_creation(self):
        self.workspace["workspace"]["properties"]["workspace_subscription_id"] = "another"
        with self.assertRaisesRegex(ValueError, "same subscription"):
            await self.run_case()
        self.arm.request.assert_not_awaited()
        self.post.assert_not_awaited()

    async def test_public_access_failure_still_cleans_up(self):
        self.account["properties"]["publicNetworkAccess"] = "Enabled"
        with self.assertRaises(AssertionError):
            await self.run_case()
        self.cleanup.assert_awaited_once_with("/api" + PATH, "token", True, allow_failed_disable=True)

    async def test_wrong_model_deployment_still_cleans_up(self):
        self.deployment["properties"]["model"]["version"] = "other"
        with self.assertRaises(AssertionError):
            await self.run_case()
        self.cleanup.assert_awaited_once()

    async def test_normal_cleanup_can_outlast_the_creation_deadline(self):
        async def cleanup(*args, **kwargs):
            await asyncio.sleep(0.1)

        self.cleanup.side_effect = cleanup
        with patch.object(lifecycle, "CREATE_TIMEOUT_SECONDS", 0.05):
            await self.run_case()
        self.cleanup.assert_awaited_once()

    async def test_verification_timeout_still_cleans_up(self):
        async def block_account(method, identifier, api, **kwargs):
            if identifier == GROUP:
                return {"location": "westeurope"}
            await asyncio.Event().wait()
            raise AssertionError("The blocking ARM request unexpectedly resumed")

        self.arm.request.side_effect = block_account
        with patch.object(lifecycle, "VERIFY_TIMEOUT_SECONDS", 0.01), self.assertRaises(TimeoutError):
            await self.run_case()
        self.cleanup.assert_awaited_once()

    async def test_cleanup_failure_is_not_success(self):
        self.cleanup.side_effect = RuntimeError("delete failed")
        with self.assertRaisesRegex(RuntimeError, "delete failed"):
            await self.run_case()

    async def test_retained_api_record_or_account_is_not_success(self):
        for api_status, retained in ((200, False), (404, True)):
            self.lookup_status, self.retained = api_status, retained
            with self.subTest(api=api_status, retained=retained), self.assertRaises(AssertionError):
                await self.run_case()
