"""Read OHDSI infrastructure without requesting application settings or secrets."""

import asyncio
from copy import deepcopy
from dataclasses import dataclass
import os
import re

from e2e_tests import config
from e2e_tests.resources.ohdsi_lifecycle import require_uuid

TEMPLATE = "tre-workspace-service-ohdsi"
FIREWALL = "tre-shared-service-firewall"
BASE = "tre-workspace-base"
WEB_API = "2024-04-01"
POSTGRES_API = "2024-08-01"
NETWORK_API = "2024-05-01"
DNS_API = "2024-06-01"
GROUP_API = "2021-04-01"
IDENTITY_API = "2023-01-31"
STORAGE_API = "2023-05-01"
ROLE_API = "2022-04-01"
SECRETS_USER = "4633458b-17de-408a-b874-0445c86b69e6"


@dataclass(frozen=True)
class Settings:
    subscription: str
    tenant: str
    tre_id: str

    def __post_init__(self):
        require_uuid(self.subscription)
        require_uuid(self.tenant)
        if not isinstance(self.tre_id, str) or not re.fullmatch(r"[a-z0-9-]{1,11}", self.tre_id):
            raise ValueError("OHDSI requires a valid TRE_ID shorter than 12 characters")

    @property
    def group(self):
        return f"/subscriptions/{self.subscription}/resourceGroups/rg-{self.tre_id}"


def require_settings():
    if os.environ.get("AZURE_ENVIRONMENT", "AzureCloud") != "AzureCloud":
        raise ValueError("OHDSI validation currently supports AzureCloud only")
    settings = Settings(os.environ.get("ARM_SUBSCRIPTION_ID", ""), os.environ.get("ARM_TENANT_ID", ""), config.TRE_ID)
    if require_uuid(config.AAD_TENANT_ID) != settings.tenant:
        raise ValueError("OHDSI requires matching deployment and authentication tenants")
    return settings


def resource_ids(settings, workspace_id, service_id):
    require_uuid(workspace_id)
    require_uuid(service_id)
    ws = f"{settings.tre_id}-ws-{workspace_id[-4:]}"
    suffix = f"{ws}-svc-{service_id[-4:]}"
    group = f"/subscriptions/{settings.subscription}/resourceGroups/rg-{ws}"
    vnet = f"{group}/providers/Microsoft.Network/virtualNetworks/vnet-{ws}"
    apps = {key: f"{group}/providers/Microsoft.Web/sites/app-ohdsi-{key}-{suffix}" for key in ("atlas", "webapi")}
    endpoints = {
        key: f"{group}/providers/Microsoft.Network/privateEndpoints/pe-{app.rsplit('/', 1)[1]}"
        for key, app in apps.items()
    }
    storage = f"{group}/providers/Microsoft.Storage/storageAccounts/{('stg' + ws[-8:]).replace('-', '').lower()}"
    ids = {
        "group": group,
        "vnet": vnet,
        "apps": apps,
        "endpoints": endpoints,
        "postgres": f"{group}/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-server-{suffix}",
        "postgres_subnet": f"{vnet}/subnets/PostgreSQLSubnet{service_id[-4:]}",
        "nsg": f"{group}/providers/Microsoft.Network/networkSecurityGroups/nsg-psql-{suffix}",
        "identity": f"{group}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-ohdsi-webapi-{suffix}",
        "share": f"{storage}/fileServices/default/shares/atlas-{suffix}",
        "vault": f"{group}/providers/Microsoft.KeyVault/vaults/kv-{ws[-20:].lower()}",
        "web_zone": f"{settings.group}/providers/Microsoft.Network/privateDnsZones/privatelink.azurewebsites.net",
        "pg_zone": f"{settings.group}/providers/Microsoft.Network/privateDnsZones/privatelink.postgres.database.azure.com",
    }
    ids["removal"] = [(value, WEB_API) for value in apps.values()] + [
        (value, NETWORK_API) for value in endpoints.values()
    ]
    ids["removal"] += [
        (ids[key], version)
        for key, version in (
            ("postgres", POSTGRES_API),
            ("postgres_subnet", NETWORK_API),
            ("nsg", NETWORK_API),
            ("identity", IDENTITY_API),
            ("share", STORAGE_API),
        )
    ]
    return ids


def same_id(actual, expected):
    assert isinstance(actual, str) and actual.lower() == expected.lower(), "Unexpected OHDSI ARM resource ID"


def owned(resource, identifier, tags):
    same_id(resource.get("id"), identifier)
    assert all(resource.get("tags", {}).get(key) == value for key, value in tags.items()), "OHDSI ownership tags differ"


async def guard_owned(arm, ids, tags):
    for identifier, api in (
        [(v, WEB_API) for v in ids["apps"].values()]
        + [(ids["postgres"], POSTGRES_API), (ids["identity"], IDENTITY_API), (ids["nsg"], NETWORK_API)]
        + [(v, NETWORK_API) for v in ids["endpoints"].values()]
    ):
        resource = await arm.request("GET", identifier, api, missing_ok=True)
        if resource is not None:
            owned(resource, identifier, tags)


async def preflight(arm, settings):
    group = await arm.request("GET", settings.group, GROUP_API)
    owned(group, settings.group, {"tre_id": settings.tre_id})
    for zone in ("privatelink.azurewebsites.net", "privatelink.postgres.database.azure.com"):
        identifier = f"{settings.group}/providers/Microsoft.Network/privateDnsZones/{zone}"
        owned(await arm.request("GET", identifier, DNS_API), identifier, {"tre_id": settings.tre_id})


async def postgres_core_dns_link(arm, settings, *, missing_ok=False):
    identifier = (
        f"{settings.group}/providers/Microsoft.Network/privateDnsZones/"
        "privatelink.postgres.database.azure.com/virtualNetworkLinks/core"
    )
    link = await arm.request("GET", identifier, DNS_API, missing_ok=missing_ok)
    if link is None:
        assert missing_ok, "Shared PostgreSQL core DNS link is missing"
        return None
    same_id(link.get("id"), identifier)
    properties = link["properties"]
    same_id(
        properties.get("virtualNetwork", {}).get("id"),
        f"{settings.group}/providers/Microsoft.Network/virtualNetworks/vnet-{settings.tre_id}",
    )
    assert properties.get("registrationEnabled") is False, "Shared PostgreSQL DNS registration changed"
    assert properties.get("provisioningState") == "Succeeded", "Shared PostgreSQL core DNS link is not ready"
    return link


def validate_app(app, configuration, identifier, ids, tags, key):
    owned(app, identifier, tags)
    props = app["properties"]
    assert props.get("state") == "Running", "OHDSI web app is not running"
    assert props.get("publicNetworkAccess") == "Disabled", "OHDSI web app permits public access"
    assert props.get("httpsOnly") is True, "OHDSI web app permits HTTP"
    same_id(props.get("virtualNetworkSubnetId"), ids["vnet"] + "/subnets/WebAppsSubnet")
    site = configuration["properties"]
    assert site.get("ftpsState") == "Disabled", "OHDSI web app permits FTP"
    assert site.get("minTlsVersion") == "1.3", "OHDSI web app TLS setting differs"
    assert site.get("linuxFxVersion") == f"DOCKER|index.docker.io/ohdsi/{key}:2.12.1", "OHDSI image differs"
    if key == "webapi":
        identity = app.get("identity", {})
        assert identity.get("type") == "UserAssigned", "Unexpected OHDSI application identity type"
        assert {k.lower() for k in identity.get("userAssignedIdentities", {})} == {ids["identity"].lower()}
        same_id(props.get("keyVaultReferenceIdentity"), ids["identity"])


async def validate_resources(arm, settings, ids, tags):
    async with asyncio.timeout(10 * 60):
        postgres = await arm.request("GET", ids["postgres"], POSTGRES_API)
        owned(postgres, ids["postgres"], tags)
        props = postgres["properties"]
        assert props.get("state") == "Ready", "OHDSI PostgreSQL is not ready"
        assert props.get("version") == "14", "OHDSI PostgreSQL version differs"
        assert props.get("network", {}).get("publicNetworkAccess") == "Disabled", "PostgreSQL permits public access"
        same_id(props["network"].get("delegatedSubnetResourceId"), ids["postgres_subnet"])
        same_id(props["network"].get("privateDnsZoneArmResourceId"), ids["pg_zone"])
        subnet = await arm.request("GET", ids["postgres_subnet"], NETWORK_API)
        same_id(subnet.get("id"), ids["postgres_subnet"])
        same_id(subnet["properties"].get("networkSecurityGroup", {}).get("id"), ids["nsg"])
        assert subnet["properties"].get("defaultOutboundAccess") is False
        assert any(
            d.get("properties", {}).get("serviceName") == "Microsoft.DBforPostgreSQL/flexibleServers"
            for d in subnet["properties"].get("delegations", [])
        )
        for key, identifier in ids["apps"].items():
            app = await arm.request("GET", identifier, WEB_API)
            configuration = await arm.request("GET", identifier + "/config/web", WEB_API)
            validate_app(app, configuration, identifier, ids, tags, key)
            endpoint = await arm.request("GET", ids["endpoints"][key], NETWORK_API)
            owned(endpoint, ids["endpoints"][key], tags)
            properties = endpoint["properties"]
            assert properties.get("provisioningState") == "Succeeded"
            same_id(properties.get("subnet", {}).get("id"), ids["vnet"] + "/subnets/ServicesSubnet")
            assert not properties.get("manualPrivateLinkServiceConnections")
            connections = properties.get("privateLinkServiceConnections", [])
            assert len(connections) == 1
            connection = connections[0]["properties"]
            same_id(connection.get("privateLinkServiceId"), identifier)
            assert connection.get("groupIds") == ["sites"]
            assert connection.get("privateLinkServiceConnectionState", {}).get("status") == "Approved"
            zone_group_id = ids["endpoints"][key] + "/privateDnsZoneGroups/privatelink.azurewebsites.net"
            zone_group = await arm.request("GET", zone_group_id, NETWORK_API)
            same_id(zone_group.get("id"), zone_group_id)
            zones = zone_group["properties"].get("privateDnsZoneConfigs", [])
            assert len(zones) == 1
            same_id(zones[0]["properties"].get("privateDnsZoneId"), ids["web_zone"])
        identity = await arm.request("GET", ids["identity"], IDENTITY_API)
        owned(identity, ids["identity"], tags)
        assert require_uuid(identity["properties"].get("tenantId")) == settings.tenant
        principal = require_uuid(identity["properties"].get("principalId"))
        assignments = await arm.request(
            "GET", ids["vault"] + "/providers/Microsoft.Authorization/roleAssignments", ROLE_API
        )
        assert isinstance(assignments.get("value"), list) and not assignments.get("nextLink"), (
            "Incomplete OHDSI role inventory"
        )
        roles = [
            r["properties"] for r in assignments["value"] if r["properties"].get("principalId", "").lower() == principal
        ]
        assert len(roles) == 1, "Unexpected OHDSI vault role count"
        same_id(roles[0].get("scope"), ids["vault"])
        assert roles[0].get("roleDefinitionId", "").rsplit("/", 1)[-1].lower() == SECRETS_USER
        return principal


def firewall_rules(resource):
    return {
        key: deepcopy(resource["properties"].get(key, [])) for key in ("network_rule_collections", "rule_collections")
    }


def validate_firewall(resource, baseline, service_id, prefixes):
    rules = firewall_rules(resource)
    for key, prefix in (("network_rule_collections", "nrc"), ("rule_collections", "arc")):
        name = f"{prefix}_svc_{service_id}"
        matches = [c for c in rules[key] if c.get("name") == name]
        assert len(matches) == 1, "OHDSI firewall collection is missing or duplicated"
        collection = matches[0]
        rules[key].remove(collection)
        assert collection["action"] == "Allow" and len(collection["rules"]) == 1
        rule = collection["rules"][0]
        assert set(rule["source_addresses"]) == set(prefixes)
        if prefix == "nrc":
            assert rule["destination_addresses"] == ["AzureActiveDirectory"]
            assert rule["destination_ports"] == ["*"] and rule["protocols"] == ["TCP"]
        else:
            assert rule["protocols"] == [{"port": "80", "type": "Http"}, {"port": "443", "type": "Https"}]
            assert set(rule["target_fqdns"]) == {
                "*.msftauth.net",
                "*.msauth.net",
                "login.microsoftonline.com",
                "aadcdn.msftauthimages.net",
                "aadcdn.msauthimages.net",
                "*.login.live.com",
                "*.microsoftonline-p.com",
                "msft.sts.microsoft.com",
            }
    assert rules == baseline, "Unrelated firewall collections changed"


async def assert_removed(arm, identifiers):
    async with asyncio.timeout(5 * 60):
        for identifier, api in identifiers:
            while await arm.request("GET", identifier, api, missing_ok=True) is not None:
                await asyncio.sleep(10)


async def assert_roles_removed(arm, vault, principal):
    async with asyncio.timeout(5 * 60):
        while True:
            roles = await arm.request("GET", vault + "/providers/Microsoft.Authorization/roleAssignments", ROLE_API)
            assert isinstance(roles.get("value"), list) and not roles.get("nextLink"), (
                "Incomplete OHDSI cleanup role inventory"
            )
            if not any(r["properties"].get("principalId", "").lower() == principal for r in roles["value"]):
                return
            await asyncio.sleep(10)
