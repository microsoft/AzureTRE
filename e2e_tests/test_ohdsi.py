"""Validate a private OHDSI deployment without an external clinical data source."""

from uuid import uuid4

import pytest

from e2e_tests import config
from e2e_tests.bundle_evidence import record_deployed_resource, record_reused_resource
from e2e_tests.conftest import get_workspace_owner_token
from e2e_tests.helpers import get_admin_token
from e2e_tests.resources.ohdsi import (
    BASE,
    FIREWALL,
    TEMPLATE,
    GROUP_API,
    IDENTITY_API,
    DNS_API,
    assert_removed,
    assert_roles_removed,
    firewall_rules,
    guard_owned,
    owned,
    postgres_core_dns_link,
    preflight,
    require_settings,
    resource_ids,
    validate_firewall,
    validate_resources,
)
from e2e_tests.resources.ohdsi_lifecycle import ohdsi_lifecycle, require_uuid
from e2e_tests.resources.resource import get_resource
from e2e_tests.resources.sql_probe import arm_client
from e2e_tests.run_bundle import load_catalog


async def prerequisites(verify):
    catalog = load_catalog()
    token = await get_admin_token(verify)
    for name, kind in ((TEMPLATE, "workspace-service"), (BASE, "workspace"), (FIREWALL, "shared-service")):
        template = await get_resource(f"/api/{kind}-templates/{name}", token, verify)
        if template["name"] != name or template["version"] != catalog[name]["source_version"]:
            raise ValueError(f"Register the checkout version of {name} before OHDSI validation")
    services = (await get_resource("/api/shared-services", token, verify))["sharedServices"]
    firewalls = [s for s in services if s["templateName"] == FIREWALL]
    if len(firewalls) != 1:
        raise ValueError("OHDSI requires exactly one deployed firewall")
    firewall = firewalls[0]
    if (
        firewall["isEnabled"] is not True
        or firewall["deploymentStatus"] not in ("deployed", "updated")
        or firewall["templateVersion"] != catalog[FIREWALL]["source_version"]
    ):
        raise ValueError("Deploy and enable the checkout firewall version before OHDSI validation")
    record_reused_resource(firewall)
    return firewall


def payload(template, label, **properties):
    return {
        "templateName": template,
        "properties": {
            "display_name": f"OHDSI validation {label} {uuid4()}",
            "description": "Owned OHDSI lifecycle validation",
            **properties,
        },
    }


async def validate_lifecycle(verify):
    settings = require_settings()
    async with arm_client() as arm:
        async with ohdsi_lifecycle(verify) as resources:
            firewall = await prerequisites(verify)
            baseline = firewall_rules(firewall)
            await preflight(arm, settings)
            core_link = await postgres_core_dns_link(arm, settings, missing_ok=True)
            workspace_path = None
            workspace_id = None
            callbacks = None
            principal = None

            async def check_core_link(*, required=False):
                nonlocal core_link
                # A failed install might not reach DNS creation. Preserve any link
                # observed before install, during validation or before removal.
                core_link = await postgres_core_dns_link(arm, settings, missing_ok=not required and core_link is None)

            async def current_firewall():
                result = (
                    await get_resource(f"/api/shared-services/{firewall['id']}", await get_admin_token(verify), verify)
                )["sharedService"]
                assert result["id"] == firewall["id"] and result["templateName"] == FIREWALL
                return result

            async def workspace_record():
                return (await get_resource(f"/api{workspace_path}", await get_admin_token(verify), verify))["workspace"]

            def group_id(identifier):
                return (
                    f"/subscriptions/{settings.subscription}/resourceGroups/rg-{settings.tre_id}-ws-{identifier[-4:]}"
                )

            async def guard_workspace(_path, identifier):
                group = await arm.request("GET", group_id(identifier), GROUP_API, missing_ok=True)
                if group is not None:
                    owned(group, group_id(identifier), {"tre_id": settings.tre_id, "tre_workspace_id": identifier})

            async def removed_workspace(_path, identifier):
                await assert_removed(arm, [(group_id(identifier), GROUP_API)])

            properties = {"auth_type": "Automatic", "address_space_size": "small", "enable_backup": False}
            if config.TEST_WORKSPACE_APP_PLAN:
                properties["app_service_plan_sku"] = config.TEST_WORKSPACE_APP_PLAN
            workspace_path, workspace_id = await resources.create(
                payload(BASE, "workspace", **properties),
                "/api/workspaces",
                before_remove=guard_workspace,
                after_remove=removed_workspace,
            )
            workspace = await workspace_record()
            assert workspace["templateVersion"] == load_catalog()[BASE]["source_version"]
            assert workspace["properties"]["auth_type"] == "Automatic"
            assert (
                workspace["properties"].get("workspace_subscription_id") or settings.subscription
            ).lower() == settings.subscription
            record_deployed_resource(workspace, workspace_path)
            callbacks = list(workspace["properties"].get("aad_redirect_uris", []))
            await guard_workspace(workspace_path, workspace_id)

            async def guard_service(_path, identifier):
                nonlocal principal
                ids = resource_ids(settings, workspace_id, identifier)
                await guard_workspace(workspace_path, workspace_id)
                await guard_owned(
                    arm,
                    ids,
                    {
                        "tre_id": settings.tre_id,
                        "tre_workspace_id": workspace_id,
                        "tre_workspace_service_id": identifier,
                    },
                )
                identity = await arm.request("GET", ids["identity"], IDENTITY_API, missing_ok=True)
                if identity is not None:
                    principal = require_uuid(identity["properties"]["principalId"])
                await check_core_link()

            async def removed_service(_path, identifier):
                ids = resource_ids(settings, workspace_id, identifier)
                dns_records = [
                    (f"{ids['web_zone']}/A/{app.rsplit('/', 1)[1]}{suffix}", DNS_API)
                    for app in ids["apps"].values()
                    for suffix in ("", ".scm")
                ]
                await assert_removed(arm, ids["removal"] + dns_records)
                await check_core_link()
                if principal:
                    await assert_roles_removed(arm, ids["vault"], principal)
                assert firewall_rules(await current_firewall()) == baseline, "OHDSI firewall rules were not restored"
                assert (await workspace_record())["properties"].get("aad_redirect_uris", []) == callbacks, (
                    "OHDSI callback was not removed"
                )

            service_path, service_id = await resources.create(
                payload(TEMPLATE, "service", configure_data_source=False),
                f"/api{workspace_path}/workspace-services",
                workspace_id,
                before_remove=guard_service,
                after_remove=removed_service,
            )
            ids = resource_ids(settings, workspace_id, service_id)

            async def inspect(record):
                await check_core_link(required=True)
                assert (
                    record["id"] == service_id
                    and record["templateVersion"] == load_catalog()[TEMPLATE]["source_version"]
                )
                record_deployed_resource(record, service_path)
                props = record["properties"]
                assert props["configure_data_source"] is False
                assert props["is_exposed_externally"] is False
                assert (
                    props["connection_uri"]
                    == "https://" + ids["apps"]["atlas"].rsplit("/", 1)[1] + ".azurewebsites.net/atlas"
                )
                assert (
                    props["webapi_uri"]
                    == "https://" + ids["apps"]["webapi"].rsplit("/", 1)[1] + ".azurewebsites.net/WebAPI/"
                )
                expected_callback = props["webapi_uri"] + "user/oauth/callback?client_name=OidcClient"
                assert props["authentication_callback_uri"] == expected_callback
                parent = await workspace_record()
                entries = list(parent["properties"].get("aad_redirect_uris", []))
                expected = {"name": service_id, "value": expected_callback}
                assert entries.count(expected) == 1
                entries.remove(expected)
                assert entries == callbacks, "Unrelated workspace callbacks changed"
                validate_firewall(
                    await current_firewall(), baseline, service_id, parent["properties"]["address_spaces"]
                )
                return await validate_resources(
                    arm,
                    settings,
                    ids,
                    {
                        "tre_id": settings.tre_id,
                        "tre_workspace_id": workspace_id,
                        "tre_workspace_service_id": service_id,
                    },
                )

            record = (
                await get_resource(f"/api{service_path}", await get_workspace_owner_token(workspace_id, verify), verify)
            )["workspaceService"]
            principal = await inspect(record)
            updated = await resources.upgrade(resources.owned[-1], "OHDSI lifecycle metadata upgrade")
            assert await inspect(updated) == principal, "OHDSI upgrade replaced the managed identity"


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.ohdsi_validation
async def test_private_ohdsi_lifecycle(verify):
    await validate_lifecycle(verify)
