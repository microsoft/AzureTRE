"""Read-only ARM checks for isolated Databricks lifecycle validation."""

import asyncio
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
import json
import os
from pathlib import Path
import re
from uuid import UUID

from e2e_tests import config

DATABRICKS_API = "2024-05-01"
NETWORK_API = "2024-05-01"
DNS_API = "2024-06-01"
GROUP_API = "2021-04-01"
UDR_FILE = Path(__file__).resolve().parents[2] / "templates/workspace_services/databricks/terraform/databricks-udr.json"
DOMAIN_LISTS = (
    "logBlobStorageDomains",
    "artifactBlobStoragePrimaryDomains",
    "artifactBlobStorageSecondaryDomains",
    "metastoreDomains",
    "eventHubEndpointDomains",
)
PRIVATE_NETWORKS = tuple(ip_network(cidr) for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))


def uuid_value(value, name):
    try:
        parsed = UUID(value)
        if not parsed.int or str(parsed) != value.lower():
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"Databricks validation requires a non-zero canonical UUID for {name}") from None
    return str(parsed)


@dataclass(frozen=True)
class Settings:
    subscription: str
    tenant: str
    tre_id: str

    def __post_init__(self):
        for name in ("subscription", "tenant"):
            if uuid_value(getattr(self, name), name) != getattr(self, name):
                raise ValueError(f"Databricks {name} must use a canonical UUID")
        if not isinstance(self.tre_id, str) or not re.fullmatch(r"[a-z0-9-]{1,11}", self.tre_id):
            raise ValueError("Databricks validation requires a valid TRE_ID shorter than 12 characters")


def require_settings():
    if os.environ.get("AZURE_ENVIRONMENT", "AzureCloud") != "AzureCloud":
        raise ValueError("Databricks validation currently supports AzureCloud only")
    settings = Settings(
        uuid_value(os.environ.get("ARM_SUBSCRIPTION_ID", ""), "ARM_SUBSCRIPTION_ID"),
        uuid_value(os.environ.get("ARM_TENANT_ID", ""), "ARM_TENANT_ID"),
        config.TRE_ID,
    )
    if uuid_value(config.AAD_TENANT_ID, "AAD_TENANT_ID") != settings.tenant:
        raise ValueError("Databricks validation requires the authentication and Azure tenants to match")
    return settings


def core_ids(settings):
    group = f"/subscriptions/{settings.subscription}/resourceGroups/rg-{settings.tre_id}"
    vnet = f"{group}/providers/Microsoft.Network/virtualNetworks/vnet-{settings.tre_id}"
    return {
        "group": group,
        "vnet": vnet,
        "shared_subnet": f"{vnet}/subnets/SharedSubnet",
        "zones": {
            key: f"{group}/providers/Microsoft.Network/privateDnsZones/{name}"
            for key, name in (
                ("databricks", "privatelink.azuredatabricks.net"),
                ("dfs", "privatelink.dfs.core.windows.net"),
                ("blob", "privatelink.blob.core.windows.net"),
            )
        },
    }


def auth_ids(settings, service_id):
    return _resource_ids(settings, uuid_value(service_id, "shared service"))


def service_ids(settings, workspace_id, service_id):
    return _resource_ids(settings, uuid_value(service_id, "workspace service"), uuid_value(workspace_id, "workspace"))


def _resource_ids(settings, service_id, workspace_id=None):
    core = core_ids(settings)
    prefix = f"/subscriptions/{settings.subscription}/resourceGroups/"
    parent_suffix = f"{settings.tre_id}-ws-{workspace_id[-4:]}" if workspace_id else settings.tre_id
    suffix = f"{parent_suffix}-svc-{service_id[-4:]}"
    group = prefix + f"rg-{parent_suffix if workspace_id else suffix}"
    vnet = f"{group}/providers/Microsoft.Network/virtualNetworks/vnet-{parent_suffix if workspace_id else suffix}"
    workspace = f"{group}/providers/Microsoft.Databricks/workspaces/adb-{suffix}"
    connector = f"{group}/providers/Microsoft.Databricks/accessConnectors/adb-{suffix}-access-connector"
    endpoint_key = "cp" if workspace_id else "auth"
    endpoints = {
        key: f"{group}/providers/Microsoft.Network/privateEndpoints/pe-adb-{key}-{suffix}"
        for key in (endpoint_key, "fs", "blob")
    }
    group_parts = {endpoint_key: "control-plane" if workspace_id else "auth", "fs": "filesystem", "blob": "blob"}
    managed_group = prefix + f"rg-{'adb-' if not workspace_id else ''}{suffix}"
    result = {
        "kind": "service" if workspace_id else "auth",
        "group": group,
        "managed_group": managed_group,
        "workspace": workspace,
        "connector": connector,
        "vnet": vnet,
        "host_subnet": f"{vnet}/subnets/adb-host-subnet-{suffix}",
        "container_subnet": f"{vnet}/subnets/adb-container-subnet-{suffix}",
        "endpoint_subnet": f"{vnet}/subnets/ServicesSubnet" if workspace_id else core["shared_subnet"],
        "nsg": f"{group}/providers/Microsoft.Network/networkSecurityGroups/nsg-{suffix}",
        "route": f"{group}/providers/Microsoft.Network/routeTables/rt-{suffix}" if workspace_id else None,
        "storage": f"{managed_group}/providers/Microsoft.Storage/storageAccounts/stgdbfssvc{service_id[-4:]}"
        if workspace_id
        else None,
        "endpoints": endpoints,
        "zones": core["zones"],
        "zone_groups": {
            key: f"{endpoint}/privateDnsZoneGroups/private-dns-zone-group-databricks-{group_parts[key]}-{suffix}"
            for key, endpoint in endpoints.items()
        },
    }
    result["removal"] = [(workspace, DATABRICKS_API), (connector, DATABRICKS_API)]
    result["removal"] += [(value, NETWORK_API) for value in endpoints.values()]
    result["removal"] += [(result[key], NETWORK_API) for key in ("host_subnet", "container_subnet", "nsg")]
    result["removal"].append((managed_group, GROUP_API))
    result["removal"] += [(result["route"], NETWORK_API)] if workspace_id else [(vnet, NETWORK_API), (group, GROUP_API)]
    return result


def same_id(actual, expected):
    assert isinstance(actual, str) and actual.lower() == expected.lower(), "Unexpected Databricks ARM resource ID"


def validate_owned(resource, arm_id, tags, location=None):
    same_id(resource.get("id"), arm_id)
    assert all(resource.get("tags", {}).get(key) == value for key, value in tags.items()), (
        "Databricks ownership tags differ"
    )
    if location:
        assert resource.get("location", "").lower().replace(" ", "") == location, "Databricks resource region differs"


def list_values(response):
    assert isinstance(response, dict) and isinstance(response.get("value"), list), "Malformed ARM list response"
    assert not response.get("nextLink"), "ARM inventory is paginated; refusing an incomplete Databricks safety check"
    return response["value"]


async def assert_auth_dns_empty(arm, settings):
    zone = core_ids(settings)["zones"]["databricks"]
    records = list_values(await arm.request("GET", zone + "/aLL", DNS_API))
    for record in records:
        same_id(record.get("id"), zone + "/SOA/@")
        assert record.get("type", "").lower() == "microsoft.network/privatednszones/soa", (
            "Databricks DNS zone is in use"
        )


def require_region_endpoints(location):
    values = json.loads(UDR_FILE.read_text()).get(location)
    if not isinstance(values, dict):
        raise ValueError(f"Databricks endpoint configuration is missing for {location}")
    for key in DOMAIN_LISTS:
        entries = values.get(key)
        if (
            not isinstance(entries, list)
            or not entries
            or any(
                not isinstance(value, str)
                or not re.fullmatch(
                    r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+", value, re.I | re.ASCII
                )
                for value in entries
            )
        ):
            raise ValueError(f"Databricks endpoint configuration {key} is incomplete for {location}")


async def preflight(arm, settings, *, workspace_service=False):
    async with asyncio.timeout(5 * 60):
        ids = core_ids(settings)
        tags = {"tre_id": settings.tre_id, "tre_core_service_id": settings.tre_id}
        group = await arm.request("GET", ids["group"], GROUP_API)
        validate_owned(group, ids["group"], {"tre_id": settings.tre_id})
        location = group.get("location", "").lower().replace(" ", "")
        assert re.fullmatch(r"[a-z0-9]+", location), "Core resource group has no valid region"
        if workspace_service:
            require_region_endpoints(location)
        vnet = await arm.request("GET", ids["vnet"], NETWORK_API)
        validate_owned(vnet, ids["vnet"], tags, location)
        same_id((await arm.request("GET", ids["shared_subnet"], NETWORK_API)).get("id"), ids["shared_subnet"])
        for zone in ids["zones"].values():
            validate_owned(await arm.request("GET", zone, DNS_API), zone, tags)
        await assert_auth_dns_empty(arm, settings)
        return location


def validate_workspace(resource, ids, tags, location):
    validate_owned(resource, ids["workspace"], tags, location)
    properties = resource["properties"]
    assert resource["sku"]["name"].lower() == "premium", "Databricks SKU is not Premium"
    for key, expected in (
        ("provisioningState", "Succeeded"),
        ("publicNetworkAccess", "Disabled"),
        ("requiredNsgRules", "NoAzureDatabricksRules"),
        ("defaultStorageFirewall", "Enabled"),
    ):
        assert properties.get(key) == expected, f"Unexpected Databricks {key}"
    same_id(properties.get("managedResourceGroupId"), ids["managed_group"])
    same_id(properties.get("accessConnector", {}).get("id"), ids["connector"])
    assert properties["accessConnector"].get("identityType") == "SystemAssigned", "Unexpected access connector identity"
    parameters = properties["parameters"]
    for key in ("enableNoPublicIp", "requireInfrastructureEncryption"):
        assert parameters.get(key, {}).get("value") is True, f"Databricks {key} is not enabled"
    same_id(parameters.get("customVirtualNetworkId", {}).get("value"), ids["vnet"])
    for parameter, key in (("customPublicSubnetName", "host_subnet"), ("customPrivateSubnetName", "container_subnet")):
        assert parameters.get(parameter, {}).get("value") == ids[key].rsplit("/", 1)[-1], "Unexpected Databricks subnet"
    storage_name = parameters.get("storageAccountName", {}).get("value", "")
    assert isinstance(storage_name, str) and re.fullmatch(r"[a-z0-9]{3,24}", storage_name), (
        "Missing Databricks storage name"
    )
    storage = f"{ids['managed_group']}/providers/Microsoft.Storage/storageAccounts/{storage_name}"
    if ids["storage"]:
        same_id(storage, ids["storage"])
    return storage


def private_addresses(values):
    assert isinstance(values, list) and values, "Missing Databricks private endpoint addresses"
    addresses = set()
    for value in values:
        address = ip_address(value)
        assert any(address in network for network in PRIVATE_NETWORKS), "Databricks endpoint has a non-private address"
        addresses.add(str(address))
    return addresses


async def validate_endpoint(arm, ids, key, tags, location, storage):
    endpoint_id = ids["endpoints"][key]
    endpoint = await arm.request("GET", endpoint_id, NETWORK_API)
    validate_owned(endpoint, endpoint_id, tags, location)
    properties = endpoint["properties"]
    assert properties.get("provisioningState") == "Succeeded", "Databricks endpoint is not provisioned"
    same_id(properties.get("subnet", {}).get("id"), ids["endpoint_subnet"])
    assert not properties.get("manualPrivateLinkServiceConnections"), "Unexpected manual Databricks endpoint connection"
    connections = properties.get("privateLinkServiceConnections", [])
    assert len(connections) == 1, "Unexpected Databricks endpoint connection count"
    connection = connections[0]["properties"]
    group = {"auth": "browser_authentication", "cp": "databricks_ui_api", "fs": "dfs", "blob": "blob"}[key]
    same_id(connection.get("privateLinkServiceId"), ids["workspace"] if key in ("auth", "cp") else storage)
    assert connection.get("groupIds") == [group], "Unexpected Databricks endpoint subgroup"
    assert connection.get("privateLinkServiceConnectionState", {}).get("status") == "Approved", (
        "Databricks endpoint is not approved"
    )
    interfaces = properties.get("networkInterfaces", [])
    assert len(interfaces) == 1, "Unexpected Databricks endpoint interface count"
    nic_id = interfaces[0].get("id", "")
    assert re.fullmatch(
        re.escape(ids["group"]) + r"/providers/Microsoft.Network/networkInterfaces/[a-zA-Z0-9_.-]+", nic_id, re.I
    ), "Databricks endpoint interface is outside its resource group"
    nic = await arm.request("GET", nic_id, NETWORK_API)
    same_id(nic.get("id"), nic_id)
    configurations = nic.get("properties", {}).get("ipConfigurations", [])
    assert configurations, "Databricks endpoint interface has no addresses"
    for item in configurations:
        same_id(item["properties"].get("subnet", {}).get("id"), ids["endpoint_subnet"])
        assert not item["properties"].get("publicIPAddress"), "Databricks endpoint interface has a public IP"
    addresses = private_addresses([item["properties"].get("privateIPAddress") for item in configurations])
    zone_id = ids["zones"]["databricks" if key in ("auth", "cp") else group]
    zone_group = await arm.request("GET", ids["zone_groups"][key], NETWORK_API)
    same_id(zone_group.get("id"), ids["zone_groups"][key])
    assert zone_group["properties"].get("provisioningState") == "Succeeded", (
        "Databricks DNS zone group is not provisioned"
    )
    zones = zone_group["properties"].get("privateDnsZoneConfigs", [])
    assert len(zones) == 1, "Unexpected Databricks DNS zone count"
    zone_config = zones[0]["properties"]
    same_id(zone_config.get("privateDnsZoneId"), zone_id)
    records = zone_config.get("recordSets", [])
    assert records, "Databricks DNS zone group has no records"
    for record in records:
        assert record.get("recordType") == "A", "Unsupported Databricks DNS record type"
        name = record.get("recordSetName", "")
        assert re.fullmatch(r"[a-zA-Z0-9_.-]+", name), "Unexpected Databricks DNS record name"
        assert private_addresses(record.get("ipAddresses")) <= addresses, (
            "Databricks DNS record does not target its endpoint"
        )
        record_id = f"{zone_id}/A/{name}"
        actual = await arm.request("GET", record_id, DNS_API)
        same_id(actual.get("id"), record_id)
        assert private_addresses(
            [entry["ipv4Address"] for entry in actual["properties"]["aRecords"]]
        ) == private_addresses(record["ipAddresses"]), "Databricks DNS addresses differ from the zone group"


async def validate_resources(arm, ids, tags, location, tenant):
    async with asyncio.timeout(10 * 60):
        resource = await arm.request("GET", ids["workspace"], DATABRICKS_API)
        storage = validate_workspace(resource, ids, tags, location)
        connector = await arm.request("GET", ids["connector"], DATABRICKS_API)
        validate_owned(connector, ids["connector"], tags, location)
        assert connector.get("properties", {}).get("provisioningState") == "Succeeded", (
            "Databricks connector is not provisioned"
        )
        identity = connector.get("identity", {})
        assert identity.get("type") == "SystemAssigned", "Unexpected Databricks connector identity type"
        assert uuid_value(identity.get("tenantId"), "connector tenant") == tenant, "Databricks connector tenant differs"
        uuid_value(identity.get("principalId"), "connector principal")
        for key in ("host_subnet", "container_subnet"):
            subnet = await arm.request("GET", ids[key], NETWORK_API)
            same_id(subnet.get("id"), ids[key])
            properties = subnet["properties"]
            assert properties.get("defaultOutboundAccess") is False, "Databricks subnet permits default outbound access"
            same_id(properties.get("networkSecurityGroup", {}).get("id"), ids["nsg"])
            assert any(
                d.get("properties", {}).get("serviceName") == "Microsoft.Databricks/workspaces"
                for d in properties.get("delegations", [])
            ), "Databricks subnet delegation is missing"
            if ids["route"]:
                same_id(properties.get("routeTable", {}).get("id"), ids["route"])
        for key in ids["endpoints"]:
            await validate_endpoint(arm, ids, key, tags, location, storage)


async def assert_removed(arm, ids):
    """Wait for all bundle-owned resources under one finite deadline."""
    async with asyncio.timeout(5 * 60):
        for resource_id, api_version in ids["removal"]:
            while await arm.request("GET", resource_id, api_version, missing_ok=True) is not None:
                await asyncio.sleep(10)
