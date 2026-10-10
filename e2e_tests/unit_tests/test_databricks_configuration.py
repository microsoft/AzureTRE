"""Reject unsafe Databricks settings and ARM lifecycle evidence."""

import asyncio
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import AsyncMock, Mock, patch

from e2e_tests.resources import databricks as db

SUBSCRIPTION = "11111111-1111-4111-8111-111111111111"
TENANT = "22222222-2222-4222-8222-222222222222"
WORKSPACE = "33333333-3333-4333-8333-333333333333"
SERVICE = "44444444-4444-4444-8444-444444444444"
PRINCIPAL = "55555555-5555-4555-8555-555555555555"
SETTINGS = db.Settings(SUBSCRIPTION, TENANT, "tre-test")
LOCATION = "switzerlandnorth"


def core_fixture():
    ids = db.core_ids(SETTINGS)
    tags = {"tre_id": SETTINGS.tre_id, "tre_core_service_id": SETTINGS.tre_id}
    resources = {
        value: {"id": value, "tags": tags, "location": LOCATION}
        for value in (ids["group"], ids["vnet"], *ids["zones"].values())
    }
    resources[ids["group"]]["tags"] = {"tre_id": SETTINGS.tre_id, "project": "Azure Trusted Research Environment"}
    resources[ids["shared_subnet"]] = {"id": ids["shared_subnet"]}
    zone = ids["zones"]["databricks"]
    resources[zone + "/aLL"] = {"value": [{"id": zone + "/SOA/@", "type": "Microsoft.Network/privateDnsZones/SOA"}]}
    return resources


def deployed_fixture(ids):
    tags = {"tre_id": SETTINGS.tre_id}
    if ids["kind"] == "auth":
        tags["tre_shared_service_id"] = SERVICE
    else:
        tags.update(tre_workspace_id=WORKSPACE, tre_workspace_service_id=SERVICE)
    storage = ids["storage"] or f"{ids['managed_group']}/providers/Microsoft.Storage/storageAccounts/authstorage123"
    resources = {
        ids["workspace"]: {
            "id": ids["workspace"],
            "tags": tags,
            "location": LOCATION,
            "sku": {"name": "premium"},
            "properties": {
                "provisioningState": "Succeeded",
                "publicNetworkAccess": "Disabled",
                "requiredNsgRules": "NoAzureDatabricksRules",
                "defaultStorageFirewall": "Enabled",
                "managedResourceGroupId": ids["managed_group"],
                "accessConnector": {"id": ids["connector"], "identityType": "SystemAssigned"},
                "parameters": {
                    "enableNoPublicIp": {"value": True},
                    "requireInfrastructureEncryption": {"value": True},
                    "customVirtualNetworkId": {"value": ids["vnet"]},
                    "customPublicSubnetName": {"value": ids["host_subnet"].rsplit("/", 1)[-1]},
                    "customPrivateSubnetName": {"value": ids["container_subnet"].rsplit("/", 1)[-1]},
                    "storageAccountName": {"value": storage.rsplit("/", 1)[-1]},
                },
            },
        },
        ids["connector"]: {
            "id": ids["connector"],
            "tags": tags,
            "location": LOCATION,
            "properties": {"provisioningState": "Succeeded"},
            "identity": {"type": "SystemAssigned", "tenantId": TENANT, "principalId": PRINCIPAL},
        },
    }
    for key in ("host_subnet", "container_subnet"):
        resources[ids[key]] = {
            "id": ids[key],
            "properties": {
                "defaultOutboundAccess": False,
                "networkSecurityGroup": {"id": ids["nsg"]},
                "delegations": [{"properties": {"serviceName": "Microsoft.Databricks/workspaces"}}],
                "routeTable": {"id": ids["route"]},
            },
        }
    for key, endpoint in ids["endpoints"].items():
        group = {"auth": "browser_authentication", "cp": "databricks_ui_api", "fs": "dfs", "blob": "blob"}[key]
        nic = f"{ids['group']}/providers/Microsoft.Network/networkInterfaces/{key}-nic"
        resources[endpoint] = {
            "id": endpoint,
            "tags": tags,
            "location": LOCATION,
            "properties": {
                "provisioningState": "Succeeded",
                "subnet": {"id": ids["endpoint_subnet"]},
                "networkInterfaces": [{"id": nic}],
                "privateLinkServiceConnections": [
                    {
                        "properties": {
                            "privateLinkServiceId": ids["workspace"] if key in ("auth", "cp") else storage,
                            "groupIds": [group],
                            "privateLinkServiceConnectionState": {"status": "Approved"},
                        }
                    }
                ],
            },
        }
        resources[nic] = {
            "id": nic,
            "properties": {
                "ipConfigurations": [
                    {
                        "properties": {
                            "privateIPAddress": "10.0.0.4",
                            "subnet": {"id": ids["endpoint_subnet"]},
                        }
                    }
                ]
            },
        }
        zone = ids["zones"]["databricks" if key in ("auth", "cp") else group]
        name = "pl-auth.switzerlandnorth" if key == "auth" else f"{key}-record"
        resources[ids["zone_groups"][key]] = {
            "id": ids["zone_groups"][key],
            "properties": {
                "provisioningState": "Succeeded",
                "privateDnsZoneConfigs": [
                    {
                        "properties": {
                            "privateDnsZoneId": zone,
                            "recordSets": [{"recordType": "A", "recordSetName": name, "ipAddresses": ["10.0.0.4"]}],
                        }
                    }
                ],
            },
        }
        record_id = f"{zone}/A/{name}"
        resources[record_id] = {"id": record_id, "properties": {"aRecords": [{"ipv4Address": "10.0.0.4"}]}}
    return resources, tags


def arm_for(resources):
    arm = Mock()
    arm.request = AsyncMock(
        side_effect=lambda method, resource_id, api_version, **kwargs: deepcopy(resources[resource_id])
    )
    return arm


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(
            patch.dict(os.environ, {"ARM_SUBSCRIPTION_ID": SUBSCRIPTION, "ARM_TENANT_ID": TENANT}, clear=True)
        )
        self.enterContext(patch.object(db.config, "AAD_TENANT_ID", TENANT))
        self.enterContext(patch.object(db.config, "TRE_ID", "tre-test"))

    def test_accepts_matching_tenants_without_new_credentials(self):
        self.assertEqual(db.require_settings(), SETTINGS)

    def test_rejects_wrong_cloud_or_tenant(self):
        with (
            patch.dict(os.environ, AZURE_ENVIRONMENT="AzureUSGovernment"),
            self.assertRaisesRegex(ValueError, "AzureCloud"),
        ):
            db.require_settings()
        with (
            patch.object(db.config, "AAD_TENANT_ID", PRINCIPAL),
            self.assertRaisesRegex(ValueError, "tenants to match"),
        ):
            db.require_settings()

    def test_rejects_missing_nil_noncanonical_and_path_identifiers(self):
        for value in (
            "",
            "00000000-0000-0000-0000-000000000000",
            SUBSCRIPTION.replace("-", ""),
            SUBSCRIPTION + "/other",
        ):
            with (
                self.subTest(value=value),
                patch.dict(os.environ, ARM_SUBSCRIPTION_ID=value),
                self.assertRaises(ValueError),
            ):
                db.require_settings()
        for value in ("tre/other", "$(id)", "abcdefghijkl", "TRE-test", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                db.Settings(SUBSCRIPTION, TENANT, value)

    def test_ids_match_both_bundle_contracts(self):
        auth = db.auth_ids(SETTINGS, SERVICE)
        self.assertTrue(auth["group"].endswith("/rg-tre-test-svc-4444"))
        self.assertTrue(auth["managed_group"].endswith("/rg-adb-tre-test-svc-4444"))
        self.assertTrue(auth["endpoint_subnet"].endswith("/vnet-tre-test/subnets/SharedSubnet"))
        service = db.service_ids(SETTINGS, WORKSPACE, SERVICE)
        self.assertTrue(service["workspace"].endswith("/workspaces/adb-tre-test-ws-3333-svc-4444"))
        self.assertTrue(service["managed_group"].endswith("/rg-tre-test-ws-3333-svc-4444"))
        self.assertTrue(service["storage"].endswith("/storageAccounts/stgdbfssvc4444"))
        self.assertNotIn((service["group"], db.GROUP_API), service["removal"])
        self.assertNotIn((service["vnet"], db.NETWORK_API), service["removal"])
        with self.assertRaises(ValueError):
            db.service_ids(SETTINGS, WORKSPACE + "/other", SERVICE)

    def test_region_configuration_rejects_missing_empty_and_unsafe_hosts(self):
        values = {name: ["valid.example.com"] for name in db.DOMAIN_LISTS}
        for value in (
            None,
            {},
            {**values, "metastoreDomains": [""]},
            {**values, "logBlobStorageDomains": []},
            {**values, "eventHubEndpointDomains": ["https://foreign.example/path"]},
            {**values, "eventHubEndpointDomains": [" valid.example.com"]},
            {**values, "eventHubEndpointDomains": ["*.example.com"]},
        ):
            with self.subTest(value=value), patch.object(db, "UDR_FILE") as source:
                source.read_text.return_value = json.dumps({LOCATION: value})
                with self.assertRaises(ValueError):
                    db.require_region_endpoints(LOCATION)

    def test_region_configuration_accepts_existing_mixed_case_dns_names(self):
        db.require_region_endpoints("germanywestcentral")


class ArmConfigurationTests(unittest.IsolatedAsyncioTestCase):
    async def test_preflight_uses_actual_region_and_only_reads(self):
        arm = arm_for(core_fixture())
        with patch.dict(os.environ, LOCATION="differentregion"):
            self.assertEqual(await db.preflight(arm, SETTINGS, workspace_service=True), LOCATION)
        self.assertTrue(all(call.args[0] == "GET" for call in arm.request.await_args_list))

    async def test_auth_does_not_require_workspace_regional_endpoints(self):
        with patch.object(db, "require_region_endpoints", side_effect=AssertionError("Unexpected lookup")):
            await db.preflight(arm_for(core_fixture()), SETTINGS)

    async def test_preflight_rejects_foreign_core_tags_and_used_or_paginated_dns(self):
        ids = db.core_ids(SETTINGS)
        for key in (ids["group"], ids["vnet"], ids["zones"]["databricks"]):
            resources = core_fixture()
            resources[key]["tags"] = {"tre_id": "foreign"}
            with self.subTest(key=key), self.assertRaisesRegex(AssertionError, "ownership"):
                await db.preflight(arm_for(resources), SETTINGS)
        for response in (
            {"value": [], "nextLink": "https://management.azure.com/more"},
            {"value": [{"id": ids["zones"]["databricks"] + "/A/old", "type": "Microsoft.Network/privateDnsZones/A"}]},
            {"value": None},
        ):
            resources = core_fixture()
            resources[ids["zones"]["databricks"] + "/aLL"] = response
            with self.subTest(response=response), self.assertRaises(AssertionError):
                await db.preflight(arm_for(resources), SETTINGS)

    async def test_valid_auth_and_workspace_resources_are_checked_without_writes(self):
        for ids in (db.auth_ids(SETTINGS, SERVICE), db.service_ids(SETTINGS, WORKSPACE, SERVICE)):
            resources, tags = deployed_fixture(ids)
            arm = arm_for(resources)
            with self.subTest(kind=ids["kind"]):
                await db.validate_resources(arm, ids, tags, LOCATION, TENANT)
                self.assertTrue(all(call.args[0] == "GET" for call in arm.request.await_args_list))

    async def test_rejects_public_network_wrong_storage_and_foreign_ownership(self):
        ids = db.service_ids(SETTINGS, WORKSPACE, SERVICE)
        resources, tags = deployed_fixture(ids)
        workspace = resources[ids["workspace"]]
        mutations = [
            ("id", ids["workspace"] + "-other"),
            ("tags", {"tre_id": "foreign"}),
            ("location", "eastus"),
            ("properties.publicNetworkAccess", "Enabled"),
            ("properties.defaultStorageFirewall", "Disabled"),
            ("properties.parameters.enableNoPublicIp.value", False),
            ("properties.parameters.requireInfrastructureEncryption.value", False),
            ("properties.parameters.storageAccountName.value", "foreignstorage"),
            ("properties.managedResourceGroupId", ids["group"]),
        ]
        for path, value in mutations:
            changed = deepcopy(workspace)
            target = changed
            *parents, key = path.split(".")
            for part in parents:
                target = target[part]
            target[key] = value
            with self.subTest(path=path), self.assertRaises(AssertionError):
                db.validate_workspace(changed, ids, tags, LOCATION)

    async def test_rejects_endpoint_subgroups_targets_dns_and_addresses(self):
        ids = db.auth_ids(SETTINGS, SERVICE)
        baseline, tags = deployed_fixture(ids)
        endpoint = ids["endpoints"]["auth"]
        nic = baseline[endpoint]["properties"]["networkInterfaces"][0]["id"]
        zone_group = ids["zone_groups"]["auth"]
        changes = [
            (
                endpoint,
                ("properties", "privateLinkServiceConnections", 0, "properties", "groupIds"),
                ["databricks_ui_api"],
            ),
            (
                endpoint,
                ("properties", "privateLinkServiceConnections", 0, "properties", "privateLinkServiceId"),
                ids["workspace"] + "-other",
            ),
            (endpoint, ("properties", "subnet", "id"), ids["vnet"] + "/subnets/foreign"),
            (nic, ("properties", "ipConfigurations", 0, "properties", "privateIPAddress"), "203.0.113.4"),
            (
                zone_group,
                ("properties", "privateDnsZoneConfigs", 0, "properties", "privateDnsZoneId"),
                ids["zones"]["blob"],
            ),
            (
                zone_group,
                ("properties", "privateDnsZoneConfigs", 0, "properties", "recordSets", 0, "ipAddresses"),
                ["10.0.0.99"],
            ),
            (
                zone_group,
                ("properties", "privateDnsZoneConfigs", 0, "properties", "recordSets", 0, "recordSetName"),
                "../../other",
            ),
        ]
        for resource, path, value in changes:
            resources = deepcopy(baseline)
            target = resources[resource]
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(AssertionError):
                await db.validate_resources(arm_for(resources), ids, tags, LOCATION, TENANT)

    async def test_rejects_wrong_connector_tenant(self):
        ids = db.auth_ids(SETTINGS, SERVICE)
        resources, tags = deployed_fixture(ids)
        resources[ids["connector"]]["identity"]["tenantId"] = PRINCIPAL
        with self.assertRaisesRegex(AssertionError, "tenant differs"):
            await db.validate_resources(arm_for(resources), ids, tags, LOCATION, TENANT)

    async def test_rejects_failed_connector(self):
        ids = db.auth_ids(SETTINGS, SERVICE)
        resources, tags = deployed_fixture(ids)
        resources[ids["connector"]]["properties"]["provisioningState"] = "Failed"
        with self.assertRaisesRegex(AssertionError, "connector is not provisioned"):
            await db.validate_resources(arm_for(resources), ids, tags, LOCATION, TENANT)

    async def test_removal_waits_for_absence_with_each_resources_api(self):
        arm = Mock(request=AsyncMock(side_effect=[{}, None, None]))
        ids = {
            "removal": [
                ("/subscriptions/example/workspace", db.DATABRICKS_API),
                ("/subscriptions/example/group", db.GROUP_API),
            ]
        }
        with patch.object(db.asyncio, "sleep", new_callable=AsyncMock) as sleep:
            await db.assert_removed(arm, ids)
            sleep.assert_awaited_once()
        self.assertEqual(arm.request.await_args_list[-1].args[2], db.GROUP_API)
        self.assertTrue(all(call.kwargs == {"missing_ok": True} for call in arm.request.await_args_list))

    async def test_removal_does_not_treat_arm_errors_as_absence(self):
        arm = Mock(request=AsyncMock(side_effect=RuntimeError("ARM HTTP 403")))
        with self.assertRaisesRegex(RuntimeError, "403"):
            await db.assert_removed(arm, db.auth_ids(SETTINGS, SERVICE))

    async def test_removal_has_one_finite_deadline(self):
        arm = Mock(request=AsyncMock(return_value={}))
        real_timeout = asyncio.timeout
        with patch.object(db.asyncio, "timeout", side_effect=lambda _: real_timeout(0.01)):
            with self.assertRaises(TimeoutError):
                await db.assert_removed(arm, db.auth_ids(SETTINGS, SERVICE))
