"""Inspect the owned CycleCloud infrastructure without reading credentials."""

import asyncio
from copy import deepcopy
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
import os
import re
from urllib.parse import parse_qsl, urlsplit
from uuid import UUID

from e2e_tests import config

COMPUTE_API = "2023-03-01"
DISK_API = "2023-10-02"
NETWORK_API = "2024-05-01"
DNS_API = "2024-06-01"
STORAGE_API = "2023-05-01"
ROLE_API = "2022-04-01"
CONTRIBUTOR = "b24988ac-6180-42a0-ab88-20f7382dd24c"
TEMPLATE = "tre-shared-service-cyclecloud"
FIREWALL = "tre-shared-service-firewall"


def uuid_value(value):
    try:
        parsed = UUID(value)
        if not parsed.int or str(parsed) != value:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise ValueError("CycleCloud requires canonical, non-zero resource UUIDs") from None
    return value


@dataclass(frozen=True)
class Settings:
    subscription: str
    tre_id: str

    def __post_init__(self):
        uuid_value(self.subscription)
        if not isinstance(self.tre_id, str) or not re.fullmatch(r"[a-z0-9-]{1,11}", self.tre_id):
            raise ValueError("CycleCloud requires a valid TRE_ID shorter than 12 characters")

    @property
    def group(self):
        return f"/subscriptions/{self.subscription}/resourceGroups/rg-{self.tre_id}"


def require_settings():
    if os.environ.get("AZURE_ENVIRONMENT", "AzureCloud") != "AzureCloud":
        raise ValueError("CycleCloud validation currently supports AzureCloud only")
    if uuid_value(os.environ.get("ARM_TENANT_ID", "")) != uuid_value(config.AAD_TENANT_ID):
        raise ValueError("CycleCloud requires the deployment and authentication tenants to match")
    return Settings(os.environ.get("ARM_SUBSCRIPTION_ID", ""), config.TRE_ID)


def same_id(actual, expected):
    assert isinstance(actual, str) and actual.lower() == expected.lower(), "Unexpected CycleCloud ARM identity"


def owned(record, identifier, tags):
    same_id(record.get("id"), identifier)
    assert all(record.get("tags", {}).get(k) == v for k, v in tags.items()), "CycleCloud ownership tags differ"


async def preflight(arm, settings):
    group = await arm.request("GET", settings.group, "2021-04-01")
    owned(group, settings.group, {"tre_id": settings.tre_id})
    location = group.get("location", "").lower().replace(" ", "")
    assert re.fullmatch(r"[a-z0-9]+", location), "Core region is missing"
    vnet = f"{settings.group}/providers/Microsoft.Network/virtualNetworks/vnet-{settings.tre_id}"
    subnet = vnet + "/subnets/SharedSubnet"
    subnet_record = await arm.request("GET", subnet, NETWORK_API)
    same_id(subnet_record.get("id"), subnet)
    prefixes = subnet_record["properties"].get("addressPrefixes") or [subnet_record["properties"]["addressPrefix"]]
    assert prefixes and all(ip_network(v).is_private for v in prefixes), "SharedSubnet must use private addresses"
    pip = f"{settings.group}/providers/Microsoft.Network/publicIPAddresses/pip-agw-{settings.tre_id}"
    fqdn = (await arm.request("GET", pip, NETWORK_API))["properties"]["dnsSettings"]["fqdn"]
    assert re.fullmatch(r"[a-z0-9.-]+\.cloudapp\.azure\.com", fqdn), "Unexpected core public DNS name"
    zone = f"{settings.group}/providers/Microsoft.Network/privateDnsZones/cyclecloud-{fqdn}"
    if await arm.request("GET", zone, DNS_API, missing_ok=True) is not None:
        raise ValueError("An existing CycleCloud DNS zone prevents isolated validation")
    blob_zone = f"{settings.group}/providers/Microsoft.Network/privateDnsZones/privatelink.blob.core.windows.net"
    same_id((await arm.request("GET", blob_zone, DNS_API)).get("id"), blob_zone)
    subscription = f"/subscriptions/{settings.subscription}"
    terms = (
        subscription
        + "/providers/Microsoft.MarketplaceOrdering/offerTypes/virtualmachine/publishers/azurecyclecloud/offers/azure-cyclecloud/plans/cyclecloud8/agreements/current"
    )
    agreement = await arm.request("GET", terms, "2021-01-01")
    if agreement.get("properties", {}).get("accepted") is not True:
        raise ValueError(
            "Accept the CycleCloud marketplace image terms before validation; this test does not accept terms"
        )
    images = await arm.request(
        "GET",
        subscription
        + f"/providers/Microsoft.Compute/locations/{location}/publishers/azurecyclecloud/artifacttypes/vmimage/offers/azure-cyclecloud/skus/cyclecloud8/versions",
        "2024-07-01",
    )
    if not isinstance(images, list) or not images or not all(i.get("name") for i in images):
        raise ValueError("The CycleCloud marketplace image is unavailable in the core region")
    return {
        "location": location,
        "vnet": vnet,
        "subnet": subnet,
        "prefixes": prefixes,
        "zone": zone,
        "blob_zone": blob_zone,
    }


def resource_ids(settings, core, identifier):
    suffix = uuid_value(identifier)[-4:]
    vm = f"cyclecloud-{suffix}"
    storage = f"stgcc{settings.tre_id}{suffix}".replace("-", "")
    group = settings.group
    return {
        "vm": f"{group}/providers/Microsoft.Compute/virtualMachines/{vm}",
        "disk": f"{group}/providers/Microsoft.Compute/disks/{vm}-osdisk",
        "nic": f"{group}/providers/Microsoft.Network/networkInterfaces/nic-cyclecloud-{settings.tre_id}-{suffix}",
        "storage": f"{group}/providers/Microsoft.Storage/storageAccounts/{storage}",
        "endpoint": f"{group}/providers/Microsoft.Network/privateEndpoints/pe-{storage}",
        "zone": core["zone"],
    }


def resource_types(ids):
    return [
        (ids[k], v)
        for k, v in (
            ("vm", COMPUTE_API),
            ("disk", DISK_API),
            ("nic", NETWORK_API),
            ("storage", STORAGE_API),
            ("endpoint", NETWORK_API),
            ("zone", DNS_API),
        )
    ]


async def guard_owned(arm, ids, tags):
    # The disk is deleted through its VM. Its generated tags are not guaranteed.
    for key, version in (
        ("vm", COMPUTE_API),
        ("nic", NETWORK_API),
        ("storage", STORAGE_API),
        ("endpoint", NETWORK_API),
        ("zone", DNS_API),
    ):
        record = await arm.request("GET", ids[key], version, missing_ok=True)
        if record is not None:
            owned(record, ids[key], tags)


async def principal_roles(arm, subscription, principal):
    uuid_value(principal)
    endpoint = f"/subscriptions/{subscription}/providers/Microsoft.Authorization/roleAssignments"
    query = {"$filter": f"principalId eq '{principal}'"}
    records = []
    for _ in range(20):
        page = await arm.request("GET", endpoint, ROLE_API, query=query)
        records.extend(page["value"])
        link = page.get("nextLink")
        if not link:
            return records
        parsed = urlsplit(link)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "management.azure.com"
            or parsed.path.lower() != endpoint.lower()
        ):
            raise ValueError("Unexpected role-assignment continuation URL")
        query = dict(parse_qsl(parsed.query))
        query.pop("api-version", None)
    raise RuntimeError("CycleCloud role-assignment pagination exceeded its bound")


async def validate_resources(arm, settings, core, ids, identifier):
    tags = {"tre_id": settings.tre_id, "tre_shared_service_id": identifier}
    records = {}
    for key, version in (
        ("vm", COMPUTE_API),
        ("nic", NETWORK_API),
        ("storage", STORAGE_API),
        ("endpoint", NETWORK_API),
        ("zone", DNS_API),
    ):
        records[key] = await arm.request("GET", ids[key], version)
        owned(records[key], ids[key], tags)
    vm = records["vm"]
    properties = vm["properties"]
    assert properties["provisioningState"] == "Succeeded"
    assert properties["hardwareProfile"]["vmSize"] == "Standard_DS3_v2"
    image = properties["storageProfile"]["imageReference"]
    assert (image["publisher"], image["offer"], image["sku"]) == ("azurecyclecloud", "azure-cyclecloud", "cyclecloud8")
    assert all(
        vm["plan"].get(k) == v
        for k, v in {"name": "cyclecloud8", "product": "azure-cyclecloud", "publisher": "azurecyclecloud"}.items()
    )
    assert vm["identity"]["type"] == "SystemAssigned"
    principal = uuid_value(vm["identity"]["principalId"])
    same_id(properties["storageProfile"]["osDisk"]["managedDisk"]["id"], ids["disk"])
    assert len(properties["networkProfile"]["networkInterfaces"]) == 1
    same_id(properties["networkProfile"]["networkInterfaces"][0]["id"], ids["nic"])
    configs = records["nic"]["properties"]["ipConfigurations"]
    assert len(configs) == 1
    ip = configs[0]["properties"]
    same_id(ip["subnet"]["id"], core["subnet"])
    assert not ip.get("publicIPAddress"), "CycleCloud VM must not have a public IP"
    assert any(ip_address(ip["privateIPAddress"]) in ip_network(cidr) for cidr in core["prefixes"])
    dns = await arm.request("GET", ids["zone"] + "/A/@", DNS_API)
    assert dns["properties"]["aRecords"] == [{"ipv4Address": ip["privateIPAddress"]}]
    link = await arm.request("GET", ids["zone"] + "/virtualNetworkLinks/cyclecloudlink-core", DNS_API)
    same_id(link["properties"]["virtualNetwork"]["id"], core["vnet"])
    storage = records["storage"]
    assert storage["sku"]["name"] == "Standard_GRS"
    assert storage["properties"]["encryption"]["requireInfrastructureEncryption"] is True
    assert storage["properties"]["allowCrossTenantReplication"] is False
    pe = records["endpoint"]["properties"]
    same_id(pe["subnet"]["id"], core["subnet"])
    connections = pe["privateLinkServiceConnections"]
    assert len(connections) == 1
    connection = connections[0]["properties"]
    same_id(connection["privateLinkServiceId"], ids["storage"])
    assert [v.lower() for v in connection["groupIds"]] == ["blob"]
    assert connection["privateLinkServiceConnectionState"]["status"] == "Approved"
    zone_group = await arm.request("GET", ids["endpoint"] + "/privateDnsZoneGroups/private-dns-zone-group", NETWORK_API)
    zones = zone_group["properties"]["privateDnsZoneConfigs"]
    assert len(zones) == 1
    same_id(zones[0]["properties"]["privateDnsZoneId"], core["blob_zone"])
    roles = await principal_roles(arm, settings.subscription, principal)
    assert all(r["properties"]["principalId"].lower() == principal for r in roles), (
        "Role query returned a different principal"
    )
    assert any(
        r["properties"]["scope"].lower() == f"/subscriptions/{settings.subscription}"
        and r["properties"]["roleDefinitionId"].lower().endswith("/" + CONTRIBUTOR)
        for r in roles
    ), "CycleCloud subscription Contributor assignment is missing"
    return principal


async def wait_power(arm, vm_id, expected):
    async with asyncio.timeout(10 * 60):
        while True:
            vm = await arm.request("GET", vm_id, COMPUTE_API, expand=True)
            codes = {s["code"] for s in vm["properties"].get("instanceView", {}).get("statuses", [])}
            if f"PowerState/{expected}" in codes:
                return
            await asyncio.sleep(10)


async def assert_removed(arm, ids, subscription, principal=None):
    async with asyncio.timeout(10 * 60):
        while True:
            remaining = [
                identifier
                for identifier, version in resource_types(ids)
                if await arm.request("GET", identifier, version, missing_ok=True) is not None
            ]
            roles = await principal_roles(arm, subscription, principal) if principal else []
            if not remaining and not roles:
                return
            await asyncio.sleep(10)


def firewall_rules(resource):
    result = {}
    for key in ("rule_collections", "network_rule_collections"):
        values = resource["properties"].get(key, [])
        result[key] = {v["name"]: deepcopy(v) for v in values}
        assert len(result[key]) == len(values), "Duplicate firewall collection names"
    return result


def validate_firewall(resource, baseline, identifier, prefixes):
    rules = firewall_rules(resource)
    for key, prefix in (("rule_collections", "arc"), ("network_rule_collections", "nrc")):
        name = f"{prefix}_svc_{identifier}_cyclecloud"
        collection = rules[key].pop(name)
        assert collection["action"] == "Allow" and len(collection["rules"]) == 1
        rule = collection["rules"][0]
        assert set(rule["source_addresses"]) == set(prefixes)
        if prefix == "arc":
            assert rule["protocols"] == [{"port": "443", "type": "Https"}]
            assert set(rule["target_fqdns"]) == {
                "github.com",
                "api.github.com",
                "codeload.github.com",
                "objects.githubusercontent.com",
            }
        else:
            assert rule["destination_addresses"] == ["AzureResourceManager"]
            assert rule["destination_ports"] == ["443"] and rule["protocols"] == ["TCP"]
    assert rules == baseline, "Unrelated firewall rules changed"
