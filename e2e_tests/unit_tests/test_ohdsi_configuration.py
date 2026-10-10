"""Check OHDSI private configuration, prerequisite rejection and workflow wiring."""

from copy import deepcopy
from contextlib import asynccontextmanager
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import yaml

from e2e_tests import test_ohdsi as case
from e2e_tests.resources import ohdsi as h

ROOT = Path(__file__).resolve().parents[2]
SUB = "11111111-1111-4111-8111-111111111111"
TENANT = "22222222-2222-4222-8222-222222222222"
WS = "33333333-3333-4333-8333-333333333333"
SERVICE = "44444444-4444-4444-8444-444444444444"
PRINCIPAL = "55555555-5555-4555-8555-555555555555"
SETTINGS = h.Settings(SUB, TENANT, "testtre")
IDS = h.resource_ids(SETTINGS, WS, SERVICE)
TAGS = {"tre_id": "testtre", "tre_workspace_id": WS, "tre_workspace_service_id": SERVICE}
CORE_LINK = IDS["pg_zone"] + "/virtualNetworkLinks/core"


def core_link():
    return {
        "id": CORE_LINK,
        "properties": {
            "virtualNetwork": {
                "id": f"{SETTINGS.group}/providers/Microsoft.Network/virtualNetworks/vnet-{SETTINGS.tre_id}"
            },
            "registrationEnabled": False,
            "provisioningState": "Succeeded",
        },
    }


def arm_records():
    def resource(identifier, properties):
        return {"id": identifier, "tags": TAGS.copy(), "properties": properties}

    records = {
        IDS["postgres"]: resource(
            IDS["postgres"],
            {
                "state": "Ready",
                "version": "14",
                "network": {
                    "publicNetworkAccess": "Disabled",
                    "delegatedSubnetResourceId": IDS["postgres_subnet"],
                    "privateDnsZoneArmResourceId": IDS["pg_zone"],
                },
            },
        ),
        IDS["postgres_subnet"]: resource(
            IDS["postgres_subnet"],
            {
                "networkSecurityGroup": {"id": IDS["nsg"]},
                "defaultOutboundAccess": False,
                "delegations": [{"properties": {"serviceName": "Microsoft.DBforPostgreSQL/flexibleServers"}}],
            },
        ),
        IDS["identity"]: resource(IDS["identity"], {"tenantId": TENANT, "principalId": PRINCIPAL}),
        IDS["vault"] + "/providers/Microsoft.Authorization/roleAssignments": {
            "value": [
                {
                    "properties": {
                        "principalId": PRINCIPAL,
                        "scope": IDS["vault"],
                        "roleDefinitionId": "/roles/" + h.SECRETS_USER,
                    }
                }
            ]
        },
    }
    for key, identifier in IDS["apps"].items():
        records[identifier] = resource(
            identifier,
            {
                "state": "Running",
                "publicNetworkAccess": "Disabled",
                "httpsOnly": True,
                "virtualNetworkSubnetId": IDS["vnet"] + "/subnets/WebAppsSubnet",
                "keyVaultReferenceIdentity": IDS["identity"],
            },
        )
        records[identifier]["identity"] = {"type": "UserAssigned", "userAssignedIdentities": {IDS["identity"]: {}}}
        records[identifier + "/config/web"] = {
            "properties": {
                "ftpsState": "Disabled",
                "minTlsVersion": "1.3",
                "linuxFxVersion": f"DOCKER|index.docker.io/ohdsi/{key}:2.12.1",
            }
        }
        endpoint = IDS["endpoints"][key]
        records[endpoint] = resource(
            endpoint,
            {
                "provisioningState": "Succeeded",
                "subnet": {"id": IDS["vnet"] + "/subnets/ServicesSubnet"},
                "privateLinkServiceConnections": [
                    {
                        "properties": {
                            "privateLinkServiceId": identifier,
                            "groupIds": ["sites"],
                            "privateLinkServiceConnectionState": {"status": "Approved"},
                        }
                    }
                ],
            },
        )
        zone_group = endpoint + "/privateDnsZoneGroups/privatelink.azurewebsites.net"
        records[zone_group] = resource(
            zone_group, {"privateDnsZoneConfigs": [{"properties": {"privateDnsZoneId": IDS["web_zone"]}}]}
        )
    return records


class ConfigurationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.records = arm_records()
        self.arm = AsyncMock()

        async def request(method, identifier, api, **kwargs):
            self.assertEqual(method, "GET")
            if kwargs.get("missing_ok"):
                return self.records.get(identifier)
            return self.records[identifier]

        self.arm.request.side_effect = request

    async def test_private_configuration_reads_no_secrets_or_app_settings(self):
        self.assertEqual(await h.validate_resources(self.arm, SETTINGS, IDS, TAGS), PRINCIPAL)
        for call in self.arm.request.await_args_list:
            self.assertNotIn("/secrets/", call.args[1])
            self.assertNotIn("/appsettings", call.args[1])

    async def test_role_cleanup_waits_for_rbac_convergence(self):
        self.arm.request.side_effect = [
            {"value": [{"properties": {"principalId": PRINCIPAL}}]},
            {"value": []},
        ]
        with patch.object(h.asyncio, "sleep", AsyncMock()) as sleep:
            await h.assert_roles_removed(self.arm, IDS["vault"], PRINCIPAL)
        self.assertEqual(self.arm.request.await_count, 2)
        sleep.assert_awaited_once_with(10)

    async def test_public_web_app_fails_configuration(self):
        self.records[IDS["apps"]["atlas"]]["properties"]["publicNetworkAccess"] = "Enabled"
        with self.assertRaisesRegex(AssertionError, "public access"):
            await h.validate_resources(self.arm, SETTINGS, IDS, TAGS)

    async def test_public_postgres_fails_configuration(self):
        self.records[IDS["postgres"]]["properties"]["network"]["publicNetworkAccess"] = "Enabled"
        with self.assertRaisesRegex(AssertionError, "public access"):
            await h.validate_resources(self.arm, SETTINGS, IDS, TAGS)

    async def test_wrong_tenant_or_vault_role_is_rejected(self):
        self.records[IDS["identity"]]["properties"]["tenantId"] = SUB
        with self.assertRaises(AssertionError):
            await h.validate_resources(self.arm, SETTINGS, IDS, TAGS)
        self.records = arm_records()
        self.records[IDS["vault"] + "/providers/Microsoft.Authorization/roleAssignments"]["value"][0]["properties"][
            "scope"
        ] = SETTINGS.group
        with self.assertRaises(AssertionError):
            await h.validate_resources(self.arm, SETTINGS, IDS, TAGS)

    async def test_paginated_roles_are_not_treated_as_complete(self):
        self.records[IDS["vault"] + "/providers/Microsoft.Authorization/roleAssignments"]["nextLink"] = "next-page"
        with self.assertRaisesRegex(AssertionError, "Incomplete"):
            await h.validate_resources(self.arm, SETTINGS, IDS, TAGS)

    async def test_wrong_owner_blocks_cleanup_guard(self):
        self.records[IDS["postgres"]]["tags"]["tre_workspace_service_id"] = WS
        with self.assertRaisesRegex(AssertionError, "ownership"):
            await h.guard_owned(self.arm, IDS, TAGS)

    async def test_removal_does_not_treat_api_failure_as_absence(self):
        self.arm.request.side_effect = RuntimeError("HTTP 403")
        with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
            await h.assert_removed(self.arm, [(IDS["postgres"], h.POSTGRES_API)])

    def test_ids_remain_in_owned_workspace(self):
        self.assertTrue(IDS["apps"]["atlas"].endswith("/app-ohdsi-atlas-testtre-ws-3333-svc-4444"))
        self.assertTrue(IDS["postgres_subnet"].endswith("/PostgreSQLSubnet4444"))
        self.assertTrue(all(identifier.startswith(IDS["group"] + "/") for identifier, _ in IDS["removal"]))
        for value in ("", "../other", "00000000-0000-0000-0000-000000000000"):
            with self.assertRaises(ValueError):
                h.resource_ids(SETTINGS, value, SERVICE)

    def test_firewall_restores_unrelated_collections(self):
        schema = json.loads((ROOT / "templates/workspace_services/ohdsi/template_schema.json").read_text())
        props = schema["pipeline"]["install"][-1]["properties"]
        baseline = {"network_rule_collections": [{"name": "unrelated", "rules": []}], "rule_collections": []}
        actual = {"properties": deepcopy(baseline)}
        for prop in props:
            collection = deepcopy(prop["value"])
            collection["name"] = collection["name"].replace("{{ resource.id }}", SERVICE)
            collection["rules"][0]["source_addresses"] = ["10.0.1.0/24"]
            actual["properties"][prop["name"]].append(collection)
        h.validate_firewall(actual, baseline, SERVICE, ["10.0.1.0/24"])
        actual["properties"]["network_rule_collections"][0]["rules"] = ["changed"]
        with self.assertRaisesRegex(AssertionError, "Unrelated"):
            h.validate_firewall(actual, baseline, SERVICE, ["10.0.1.0/24"])

    def test_deadline_starts_before_container_setup_and_is_forwarded(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/deploy_tre_reusable.yml").read_text())
        jobs = [
            j
            for j in workflow["jobs"].values()
            if any(s.get("name") == "Reserve OHDSI cleanup and reporting time" for s in j.get("steps", []))
        ]
        self.assertEqual(len(jobs), 1)
        steps = jobs[0]["steps"]
        deadline = next(i for i, s in enumerate(steps) if s.get("name") == "Reserve OHDSI cleanup and reporting time")
        run = next(i for i, s in enumerate(steps) if s.get("name") == "Run E2E Tests")
        self.assertLess(deadline, run)
        self.assertIn("270 * 60", steps[deadline]["run"])
        self.assertIn("inputs.e2eBundle == 'tre-workspace-service-ohdsi'", steps[deadline]["if"])
        self.assertIn("OHDSI_VALIDATION_DEADLINE=${{ env.OHDSI_VALIDATION_DEADLINE }}", steps[run]["with"]["COMMAND"])
        self.assertEqual(jobs[0]["timeout-minutes"], 300)
        self.assertIn("e2e_tests_smoke", jobs[0]["needs"])


class PrerequisiteTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_firewall_is_rejected(self):
        async def get(endpoint, *args):
            if endpoint == "/api/shared-services":
                return {"sharedServices": []}
            name = endpoint.rsplit("/", 1)[1]
            return {"name": name, "version": case.load_catalog()[name]["source_version"]}

        with (
            patch.object(case, "get_admin_token", AsyncMock(return_value="token")),
            patch.object(case, "get_resource", side_effect=get),
        ):
            with self.assertRaisesRegex(ValueError, "exactly one"):
                await case.prerequisites(True)

    async def test_stale_template_is_rejected(self):
        with (
            patch.object(case, "get_admin_token", AsyncMock(return_value="token")),
            patch.object(case, "get_resource", AsyncMock(return_value={"name": h.TEMPLATE, "version": "0.0.0"})),
        ):
            with self.assertRaisesRegex(ValueError, "checkout version"):
                await case.prerequisites(True)


class SharedDnsTests(unittest.IsolatedAsyncioTestCase):
    async def test_core_link_requires_expected_target_and_settings(self):
        arm = AsyncMock()
        arm.request.return_value = core_link()
        self.assertEqual(await h.postgres_core_dns_link(arm, SETTINGS), core_link())
        for key, value in (
            ("virtualNetwork", {"id": IDS["vnet"]}),
            ("registrationEnabled", True),
            ("provisioningState", "Failed"),
        ):
            with self.subTest(key=key):
                link = core_link()
                link["properties"][key] = value
                arm.request.return_value = link
                with self.assertRaises(AssertionError):
                    await h.postgres_core_dns_link(arm, SETTINGS)

    async def test_core_link_does_not_treat_read_failure_as_absence(self):
        arm = AsyncMock()
        arm.request.side_effect = RuntimeError("HTTP 403")
        with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
            await h.postgres_core_dns_link(arm, SETTINGS, missing_ok=True)

    async def exercise_cleanup(self, *, existing=True, create_link=False, damage=None):
        records = {CORE_LINK: core_link()} if existing else {}
        arm = AsyncMock()
        arm.__aenter__.return_value = arm
        workspace_path = f"/workspaces/{WS}"
        workspace = {
            "templateVersion": case.load_catalog()[h.BASE]["source_version"],
            "properties": {"auth_type": "Automatic", "aad_redirect_uris": []},
        }
        firewall = {"id": "firewall", "templateName": h.FIREWALL, "properties": {}}
        events = []

        async def request(method, identifier, api, **kwargs):
            self.assertEqual(method, "GET")
            if identifier == CORE_LINK:
                events.append("read link")
                value = records.get(identifier)
                if value is None and not kwargs.get("missing_ok"):
                    raise AssertionError("Shared PostgreSQL core DNS link is missing")
                return value
            if identifier == IDS["group"]:
                return {"id": identifier, "tags": {"tre_id": SETTINGS.tre_id, "tre_workspace_id": WS}}
            self.assertEqual(identifier, IDS["identity"])
            return None

        async def create(payload, endpoint, *args, **kwargs):
            if endpoint == "/api/workspaces":
                self.assertEqual(events, ["read link"])
                return workspace_path, WS
            # Exercise cleanup after a partial install, before normal inspection.
            if create_link:
                records[CORE_LINK] = core_link()
            await kwargs["before_remove"]("service", SERVICE)
            events.append("remove service")
            if damage == "delete":
                records.pop(CORE_LINK)
            elif damage == "retarget":
                records[CORE_LINK]["properties"]["virtualNetwork"]["id"] = IDS["vnet"]
            await kwargs["after_remove"]("service", SERVICE)
            raise RuntimeError("simulated partial install")

        @asynccontextmanager
        async def lifecycle(_verify):
            yield SimpleNamespace(create=create)

        arm.request.side_effect = request
        with (
            patch.object(case, "arm_client", return_value=arm),
            patch.object(case, "ohdsi_lifecycle", lifecycle),
            patch.object(case, "require_settings", return_value=SETTINGS),
            patch.object(case, "prerequisites", AsyncMock(return_value=firewall)),
            patch.object(case, "preflight", AsyncMock()),
            patch.object(case, "guard_owned", AsyncMock()),
            patch.object(case, "assert_removed", AsyncMock()),
            patch.object(case, "get_admin_token", AsyncMock(return_value="token")),
            patch.object(case, "record_deployed_resource"),
            patch.object(
                case, "get_resource", AsyncMock(return_value={"workspace": workspace, "sharedService": firewall})
            ),
        ):
            await case.validate_lifecycle(True)

    async def test_existing_link_survives_cleanup(self):
        with self.assertRaisesRegex(RuntimeError, "simulated partial install"):
            await self.exercise_cleanup()

    async def test_cleanup_detects_deleted_existing_or_new_link(self):
        for existing in (True, False):
            with self.subTest(existing=existing):
                with self.assertRaisesRegex(AssertionError, "core DNS link is missing"):
                    await self.exercise_cleanup(existing=existing, create_link=True, damage="delete")

    async def test_cleanup_detects_retargeted_core_link(self):
        with self.assertRaisesRegex(AssertionError, "ARM resource ID"):
            await self.exercise_cleanup(damage="retarget")

    async def test_failed_install_before_link_creation_allows_absence(self):
        with self.assertRaisesRegex(RuntimeError, "simulated partial install"):
            await self.exercise_cleanup(existing=False)
