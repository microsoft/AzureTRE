"""Check CycleCloud evidence against private infrastructure and prerequisite cases."""

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import yaml

from e2e_tests.resources import cyclecloud as cc

SUB = "11111111-1111-4111-8111-111111111111"
SERVICE = "22222222-2222-4222-8222-222222222222"
PRINCIPAL = "33333333-3333-4333-8333-333333333333"
ROOT = Path(__file__).resolve().parents[2]
CLUSTER = "172.31.254.0/24"


def nsg_rule(name, priority, access, protocol, ports, sources):
    properties = {
        "priority": priority,
        "direction": "Inbound",
        "access": access,
        "protocol": protocol,
        "sourcePortRange": "*",
        "destinationAddressPrefix": "*",
        "destinationPortRanges": [],
        "sourceAddressPrefixes": [],
    }
    if len(ports) == 1:
        properties["destinationPortRange"] = ports[0]
    else:
        properties["destinationPortRanges"] = ports
    if sources in ("AzureLoadBalancer", "VirtualNetwork"):
        properties["sourceAddressPrefix"] = sources
    else:
        properties["sourceAddressPrefixes"] = sources
    return {"name": name, "properties": properties}


def default_rules():
    return [
        nsg_rule("AllowCoreHttpsSshInbound", 100, "Allow", "Tcp", ["22", "443"], ["10.0.0.0/22"]),
        nsg_rule("AllowAzureLoadBalancerInbound", 120, "Allow", "*", ["*"], "AzureLoadBalancer"),
        nsg_rule("DenyVirtualNetworkInbound", 4096, "Deny", "*", ["*"], "VirtualNetwork"),
    ]


def cluster_rule(sources):
    return nsg_rule("AllowClusterNodesInbound", 110, "Allow", "Tcp", ["9443"], sources)


def fixture():
    settings = cc.Settings(SUB, "tre-test")
    net = settings.group + "/providers/Microsoft.Network/virtualNetworks/vnet-tre-test"
    core = {
        "vnet": net,
        "address_space": ["10.0.0.0/22"],
        "subnet": net + "/subnets/SharedSubnet",
        "prefixes": ["10.0.1.0/24"],
        "zone": settings.group
        + "/providers/Microsoft.Network/privateDnsZones/cyclecloud-tre-test.switzerlandnorth.cloudapp.azure.com",
        "blob_zone": settings.group + "/providers/Microsoft.Network/privateDnsZones/privatelink.blob.core.windows.net",
        "location": "switzerlandnorth",
    }
    ids = cc.resource_ids(settings, core, SERVICE)
    records = {
        value: {"id": value, "tags": {"tre_id": settings.tre_id, "tre_shared_service_id": SERVICE}}
        for value in ids.values()
    }
    records[ids["vm"]].update(
        identity={"type": "SystemAssigned", "principalId": PRINCIPAL},
        plan={
            "name": "cyclecloud8",
            "product": "azure-cyclecloud",
            "publisher": "azurecyclecloud",
            "promotionCode": None,
        },
        properties={
            "provisioningState": "Succeeded",
            "hardwareProfile": {"vmSize": "Standard_D4s_v5"},
            "storageProfile": {
                "imageReference": {
                    "publisher": "azurecyclecloud",
                    "offer": "azure-cyclecloud",
                    "sku": "cyclecloud8",
                    "version": "8.8.0",
                },
                "osDisk": {"managedDisk": {"id": ids["disk"]}},
            },
            "networkProfile": {"networkInterfaces": [{"id": ids["nic"]}]},
        },
    )
    records[ids["nic"]]["properties"] = {
        "networkSecurityGroup": {"id": ids["nsg"]},
        "ipConfigurations": [{"properties": {"subnet": {"id": core["subnet"]}, "privateIPAddress": "10.0.1.5"}}],
    }
    records[ids["nsg"]]["properties"] = {"securityRules": default_rules()}
    records[ids["zone"] + "/A/@"] = {"properties": {"aRecords": [{"ipv4Address": "10.0.1.5"}]}}
    records[ids["zone"] + "/virtualNetworkLinks/cyclecloudlink-core"] = {"properties": {"virtualNetwork": {"id": net}}}
    records[ids["storage"]].update(
        sku={"name": "Standard_GRS"},
        properties={"encryption": {"requireInfrastructureEncryption": True}, "allowCrossTenantReplication": False},
    )
    records[ids["endpoint"]]["properties"] = {
        "subnet": {"id": core["subnet"]},
        "privateLinkServiceConnections": [
            {
                "properties": {
                    "privateLinkServiceId": ids["storage"],
                    "groupIds": ["blob"],
                    "privateLinkServiceConnectionState": {"status": "Approved"},
                }
            }
        ],
    }
    records[ids["endpoint"] + "/privateDnsZoneGroups/private-dns-zone-group"] = {
        "properties": {"privateDnsZoneConfigs": [{"properties": {"privateDnsZoneId": core["blob_zone"]}}]}
    }
    records[f"/subscriptions/{SUB}/providers/Microsoft.Authorization/roleAssignments"] = {
        "value": [
            {
                "properties": {
                    "principalId": PRINCIPAL,
                    "scope": f"/subscriptions/{SUB}",
                    "roleDefinitionId": f"/subscriptions/{SUB}/providers/Microsoft.Authorization/roleDefinitions/{cc.CONTRIBUTOR}",
                }
            }
        ]
    }
    return settings, core, ids, records


class ConfigurationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings, self.core, self.ids, self.records = fixture()

        async def request(method, identifier, version, **kwargs):
            self.assertEqual(method, "GET")
            if kwargs.get("missing_ok"):
                return self.records.get(identifier)
            return self.records[identifier]

        self.arm = SimpleNamespace(request=AsyncMock(side_effect=request))

    async def test_private_resources_and_subscription_role_match_the_bundle(self):
        self.assertEqual(await cc.validate_resources(self.arm, self.settings, self.core, self.ids, SERVICE), PRINCIPAL)
        self.assertEqual(self.ids["storage"].rsplit("/", 1)[1], "stgcctretest2222")

    async def test_public_ip_wrong_subnet_dns_target_or_role_is_rejected(self):
        for defect in ("public_ip", "subnet", "dns", "role", "tags", "endpoint"):
            with self.subTest(defect=defect):
                _, _, _, self.records = fixture()
                ip = self.records[self.ids["nic"]]["properties"]["ipConfigurations"][0]["properties"]
                if defect == "public_ip":
                    ip["publicIPAddress"] = {"id": "public"}
                if defect == "subnet":
                    ip["subnet"]["id"] = "other"
                if defect == "dns":
                    self.records[self.ids["zone"] + "/A/@"]["properties"]["aRecords"] = []
                if defect == "tags":
                    self.records[self.ids["vm"]]["tags"]["tre_shared_service_id"] = "other"
                if defect == "endpoint":
                    self.records[self.ids["endpoint"]]["properties"]["privateLinkServiceConnections"][0]["properties"][
                        "privateLinkServiceId"
                    ] = "other"
                if defect == "role":
                    self.records[f"/subscriptions/{SUB}/providers/Microsoft.Authorization/roleAssignments"][
                        "value"
                    ] = []
                with self.assertRaises(AssertionError):
                    await cc.validate_resources(self.arm, self.settings, self.core, self.ids, SERVICE)

    async def test_network_card_allows_only_the_core_network_by_default(self):
        rules = self.records[self.ids["nsg"]]["properties"]["securityRules"]
        for defect in ("association", "workspace", "cluster", "core", "deny", "priority", "outbound_only"):
            with self.subTest(defect=defect):
                rules[:] = default_rules()
                self.records[self.ids["nic"]]["properties"]["networkSecurityGroup"] = {"id": self.ids["nsg"]}
                if defect == "association":
                    del self.records[self.ids["nic"]]["properties"]["networkSecurityGroup"]
                if defect == "workspace":
                    rules.append(nsg_rule("AllowWorkspace", 130, "Allow", "Tcp", ["443"], ["10.2.0.0/24"]))
                if defect == "cluster":
                    rules.append(cluster_rule([CLUSTER]))
                if defect == "core":
                    rules[0]["properties"]["sourceAddressPrefixes"] = ["10.0.0.0/8"]
                if defect == "deny":
                    del rules[2]
                if defect == "priority":
                    rules[2]["properties"]["priority"] = 105
                if defect == "outbound_only":
                    rules[2]["properties"]["direction"] = "Outbound"
                with self.assertRaises(AssertionError):
                    await cc.validate_resources(self.arm, self.settings, self.core, self.ids, SERVICE)
        rules[:] = default_rules()
        self.records[self.ids["nic"]]["properties"]["networkSecurityGroup"] = {"id": self.ids["nsg"]}
        self.assertEqual(await cc.validate_resources(self.arm, self.settings, self.core, self.ids, SERVICE), PRINCIPAL)

    async def test_cluster_rule_allows_exactly_the_requested_ranges(self):
        rules = self.records[self.ids["nsg"]]["properties"]["securityRules"]
        with self.assertRaises(AssertionError):
            await cc.validate_resources(self.arm, self.settings, self.core, self.ids, SERVICE, [CLUSTER])
        rules.append(cluster_rule([CLUSTER]))
        self.assertEqual(
            await cc.validate_resources(self.arm, self.settings, self.core, self.ids, SERVICE, [CLUSTER]), PRINCIPAL
        )
        rules[-1] = cluster_rule([CLUSTER, "10.2.0.0/24"])
        with self.assertRaises(AssertionError):
            await cc.validate_resources(self.arm, self.settings, self.core, self.ids, SERVICE, [CLUSTER])

    async def test_cleanup_refuses_foreign_tags_before_any_write(self):
        self.records[self.ids["storage"]]["tags"]["tre_shared_service_id"] = "other"
        with self.assertRaisesRegex(AssertionError, "ownership"):
            await cc.guard_owned(self.arm, self.ids, {"tre_id": self.settings.tre_id, "tre_shared_service_id": SERVICE})

    async def test_cleanup_refuses_a_foreign_network_security_group(self):
        self.records[self.ids["nsg"]]["tags"]["tre_shared_service_id"] = "other"
        with self.assertRaisesRegex(AssertionError, "ownership"):
            await cc.guard_owned(self.arm, self.ids, {"tre_id": self.settings.tre_id, "tre_shared_service_id": SERVICE})

    async def test_disk_cleanup_uses_the_disk_api_and_role_removal_is_checked(self):
        self.records = {}
        role_endpoint = f"/subscriptions/{SUB}/providers/Microsoft.Authorization/roleAssignments"
        self.records[role_endpoint] = {"value": [{"id": "role"}]}

        async def replicate_removal(seconds):
            self.records[role_endpoint] = {"value": []}

        with patch.object(cc.asyncio, "sleep", AsyncMock(side_effect=replicate_removal)) as sleep:
            await cc.assert_removed(self.arm, self.ids, SUB, PRINCIPAL)
        sleep.assert_awaited_once()
        self.arm.request.assert_any_await("GET", self.ids["disk"], cc.DISK_API, missing_ok=True)
        self.arm.request.assert_any_await("GET", self.ids["nsg"], cc.NETWORK_API, missing_ok=True)

    async def test_role_pagination_is_complete_and_cannot_change_authority(self):
        endpoint = f"/subscriptions/{SUB}/providers/Microsoft.Authorization/roleAssignments"
        self.arm.request.side_effect = [
            {
                "value": [1],
                "nextLink": f"https://management.azure.com{endpoint}?api-version=2022-04-01&$skiptoken=second",
            },
            {"value": [2]},
        ]
        self.assertEqual(await cc.principal_roles(self.arm, SUB, PRINCIPAL), [1, 2])
        self.arm.request.side_effect = [{"value": [], "nextLink": f"https://other.example{endpoint}"}]
        with self.assertRaisesRegex(ValueError, "continuation"):
            await cc.principal_roles(self.arm, SUB, PRINCIPAL)

    async def test_terms_and_image_failures_happen_without_writes(self):
        self.records[self.settings.group] = {
            "id": self.settings.group,
            "tags": {"tre_id": self.settings.tre_id},
            "location": self.core["location"],
        }
        self.records[self.core["vnet"]] = {
            "id": self.core["vnet"],
            "properties": {"addressSpace": {"addressPrefixes": ["10.0.0.0/22"]}},
        }
        self.records[self.core["subnet"]] = {"id": self.core["subnet"], "properties": {"addressPrefix": "10.0.1.0/24"}}
        self.records[self.settings.group + "/providers/Microsoft.Network/publicIPAddresses/pip-agw-tre-test"] = {
            "properties": {"dnsSettings": {"fqdn": "tre-test.switzerlandnorth.cloudapp.azure.com"}}
        }
        self.records[self.core["blob_zone"]] = {"id": self.core["blob_zone"]}
        del self.records[self.core["zone"]]
        agreement = f"/subscriptions/{SUB}/providers/Microsoft.MarketplaceOrdering/offerTypes/virtualmachine/publishers/azurecyclecloud/offers/azure-cyclecloud/plans/cyclecloud8/agreements/current"
        images = f"/subscriptions/{SUB}/providers/Microsoft.Compute/locations/switzerlandnorth/publishers/azurecyclecloud/artifacttypes/vmimage/offers/azure-cyclecloud/skus/cyclecloud8/versions"
        self.records[agreement] = {"properties": {"accepted": False}}
        with self.assertRaisesRegex(ValueError, "terms"):
            await cc.preflight(self.arm, self.settings)
        self.records[agreement]["properties"]["accepted"] = True
        self.records[images] = []
        with self.assertRaisesRegex(ValueError, "image is unavailable"):
            await cc.preflight(self.arm, self.settings)
        self.records[images] = [{"name": "8.8.0"}]
        self.assertEqual(await cc.preflight(self.arm, self.settings), self.core)


class FirewallTests(unittest.TestCase):
    def test_only_owned_rules_are_added_and_unrelated_rules_are_preserved(self):
        baseline = {"rule_collections": {"keep": {"name": "keep"}}, "network_rule_collections": {}}
        schema = json.loads((ROOT / "templates/shared_services/cyclecloud/template_schema.json").read_text())
        properties = {key: list(value.values()) for key, value in deepcopy(baseline).items()}
        for prop in schema["pipeline"]["install"][1]["properties"]:
            value = prop["value"]
            value["name"] = value["name"].replace("{{ resource.id }}", SERVICE)
            value["rules"][0]["source_addresses"] = ["10.0.1.0/24"]
            properties[prop["name"]].append(value)
        cc.validate_firewall({"properties": properties}, baseline, SERVICE, ["10.0.1.0/24"])
        properties["rule_collections"][0]["changed"] = True
        with self.assertRaisesRegex(AssertionError, "Unrelated"):
            cc.validate_firewall({"properties": properties}, baseline, SERVICE, ["10.0.1.0/24"])

    def test_other_services_can_change_their_own_rules(self):
        other = "55555555-5555-4555-8555-555555555555"
        first = {"rule_collections": [{"name": "keep"}, {"name": f"arc_svc_{other}_health_services"}]}
        baseline = cc.firewall_rules({"properties": first})
        self.assertEqual(baseline, {"rule_collections": {"keep": {"name": "keep"}}, "network_rule_collections": {}})
        later = {"rule_collections": [{"name": "keep"}], "network_rule_collections": [{"name": f"nrc_svc_{other}"}]}
        self.assertEqual(cc.firewall_rules({"properties": later}, SERVICE), baseline)
        later["rule_collections"].append({"name": f"arc_svc_{SERVICE}_cyclecloud"})
        self.assertNotEqual(cc.firewall_rules({"properties": later}, SERVICE), baseline)

    def test_deadline_precedes_container_and_smoke_is_a_dependency(self):
        jobs = yaml.safe_load((ROOT / ".github/workflows/deploy_tre_reusable.yml").read_text())["jobs"]
        job = jobs["e2e_tests_bundle"]
        self.assertIn("e2e_tests_smoke", job["needs"])
        reserve = next(s for s in job["steps"] if "CYCLECLOUD_VALIDATION_DEADLINE" in s.get("run", ""))
        run = next(s for s in job["steps"] if s["name"] == "Run E2E Tests")
        self.assertLess(job["steps"].index(reserve), job["steps"].index(run))
        self.assertEqual(reserve["if"], "inputs.e2eBundle == 'tre-shared-service-cyclecloud'")
        self.assertIn(
            "CYCLECLOUD_VALIDATION_DEADLINE=${{ env.CYCLECLOUD_VALIDATION_DEADLINE }}", run["with"]["COMMAND"]
        )
        self.assertGreater(job["timeout-minutes"], 270)
