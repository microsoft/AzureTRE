"""Validate isolated Databricks deployments without a cluster or browser session."""

from uuid import uuid4

import pytest

from e2e_tests import config
from e2e_tests.bundle_evidence import record_deployed_resource, record_reused_resource
from e2e_tests.conftest import get_workspace_owner_token
from e2e_tests.helpers import get_admin_token
from e2e_tests.resources import strings
from e2e_tests.resources.databricks import (
    assert_auth_dns_empty,
    assert_removed,
    auth_ids,
    preflight,
    require_settings,
    service_ids,
    validate_resources,
)
from e2e_tests.resources.databricks_lifecycle import databricks_lifecycle
from e2e_tests.resources.resource import get_resource
from e2e_tests.resources.sql_probe import arm_client
from e2e_tests.run_bundle import load_catalog

AUTH = "tre-shared-service-databricks-private-auth"
SERVICE = "tre-service-databricks"


async def require_isolation(verify, owned_auth_id=None):
    """Lists are complete in the TRE API. Never adopt an existing deployment."""
    token = await get_admin_token(verify)
    workspaces = (await get_resource(strings.API_WORKSPACES, token, verify))["workspaces"]
    if workspaces:
        raise RuntimeError(
            "Databricks validation requires no existing TRE workspaces; retain authentication if cleanup failed"
        )
    services = (await get_resource(strings.API_SHARED_SERVICES, token, verify))["sharedServices"]
    auth = [s for s in services if s["templateName"] == AUTH]
    if any(s["id"] != owned_auth_id for s in auth):
        raise RuntimeError("An existing Databricks authentication service prevents isolated validation")
    if owned_auth_id is not None and len(auth) != 1:
        raise RuntimeError("The owned Databricks authentication service is no longer the only authentication service")
    return services


async def require_templates(verify, workspace_service):
    catalog = load_catalog()
    names = [(AUTH, strings.API_SHARED_SERVICE_TEMPLATES)]
    if workspace_service:
        names.extend(
            [
                (strings.BASE_WORKSPACE, strings.API_WORKSPACE_TEMPLATES),
                (SERVICE, strings.API_WORKSPACE_SERVICE_TEMPLATES),
                (strings.FIREWALL_SHARED_SERVICE, strings.API_SHARED_SERVICE_TEMPLATES),
            ]
        )
    token = await get_admin_token(verify)
    for name, prefix in names:
        template = await get_resource(f"{prefix}/{name}", token, verify)
        if template["name"] != name or template["version"] != catalog[name]["source_version"]:
            raise ValueError(f"Register the checkout version of {name} before Databricks validation")


def require_firewall(services):
    firewalls = [s for s in services if s["templateName"] == strings.FIREWALL_SHARED_SERVICE]
    if len(firewalls) != 1:
        raise ValueError("Databricks service validation requires exactly one deployed firewall shared service")
    firewall = firewalls[0]
    if firewall["deploymentStatus"] not in ("deployed", "updated") or firewall["isEnabled"] is not True:
        raise ValueError("The firewall shared service must be enabled and successfully deployed")
    if firewall["templateVersion"] != load_catalog()[strings.FIREWALL_SHARED_SERVICE]["source_version"]:
        raise ValueError("Deploy the checkout firewall bundle version before Databricks validation")
    record_reused_resource(firewall)
    return firewall["id"]


async def deployed(resource_path, key, template, verify, workspace_id=None):
    token = await get_workspace_owner_token(workspace_id, verify) if workspace_id else await get_admin_token(verify)
    record = (await get_resource(f"/api{resource_path}", token, verify))[key]
    assert record["id"] == resource_path.rsplit("/", 1)[1]
    assert record["templateName"] == template
    assert record["templateVersion"] == load_catalog()[template]["source_version"], (
        "Deployed bundle version differs from this checkout"
    )
    record_deployed_resource(record, resource_path)
    return record


def payload(template, label, **properties):
    return {
        "templateName": template,
        "properties": {
            "display_name": f"Databricks validation {label} {uuid4()}",
            "description": "Isolated Databricks configuration and cleanup validation",
            **properties,
        },
    }


async def validate_lifecycle(verify, *, workspace_service):
    settings = require_settings()
    async with arm_client() as arm:
        async with databricks_lifecycle(verify) as resources:
            # Complete all preflight checks before creating even the auth dependency.
            await require_templates(verify, workspace_service)
            services = await require_isolation(verify)
            firewall_id = require_firewall(services) if workspace_service else None
            location = await preflight(arm, settings, workspace_service=workspace_service)

            async def guard_auth(_path, resource_id):
                await require_isolation(verify, resource_id)

            async def removed_auth(_path, resource_id):
                await assert_removed(arm, auth_ids(settings, resource_id))
                await assert_auth_dns_empty(arm, settings)

            auth_path, auth_id = await resources.create(
                payload(AUTH, "authentication"),
                strings.API_SHARED_SERVICES,
                before_remove=guard_auth,
                after_remove=removed_auth,
                protected=True,
            )
            await deployed(auth_path, "sharedService", AUTH, verify)
            await validate_resources(
                arm,
                auth_ids(settings, auth_id),
                {"tre_id": settings.tre_id, "tre_shared_service_id": auth_id},
                location,
                settings.tenant,
            )
            if not workspace_service:
                return

            async def removed_workspace(_path, resource_id):
                group = (
                    f"/subscriptions/{settings.subscription}/resourceGroups/rg-{settings.tre_id}-ws-{resource_id[-4:]}"
                )
                # The parent resource group includes its VNet and all parent artefacts.
                await assert_removed(arm, {"removal": [(group, "2021-04-01")]})

            workspace_properties = {"auth_type": "Automatic", "address_space_size": "small", "enable_backup": False}
            if config.TEST_WORKSPACE_APP_PLAN:
                workspace_properties["app_service_plan_sku"] = config.TEST_WORKSPACE_APP_PLAN
            workspace_path, workspace_id = await resources.create(
                payload(strings.BASE_WORKSPACE, "workspace", **workspace_properties),
                strings.API_WORKSPACES,
                after_remove=removed_workspace,
            )
            workspace = await deployed(workspace_path, "workspace", strings.BASE_WORKSPACE, verify)
            assert workspace["properties"]["auth_type"] == "Automatic"
            subscription = workspace["properties"].get("workspace_subscription_id") or settings.subscription
            assert subscription.lower() == settings.subscription.lower(), "Databricks requires the core subscription"

            async def removed_service(_path, resource_id):
                await assert_removed(arm, service_ids(settings, workspace_id, resource_id))
                token = await get_admin_token(verify)
                firewall = (await get_resource(f"/api/shared-services/{firewall_id}", token, verify))["sharedService"]
                for field, prefix in (("network_rule_collections", "nrc"), ("rule_collections", "arc")):
                    name = f"{prefix}_svc_{resource_id}_databricks"
                    assert all(rule["name"] != name for rule in firewall["properties"].get(field, [])), (
                        "Databricks firewall rules remain"
                    )

            service_path, service_id = await resources.create(
                payload(SERVICE, "service", is_exposed_externally=False),
                f"/api{workspace_path}/workspace-services",
                workspace_id=workspace_id,
                after_remove=removed_service,
            )
            service = await deployed(service_path, "workspaceService", SERVICE, verify, workspace_id)
            assert service["properties"]["is_exposed_externally"] is False
            await validate_resources(
                arm,
                service_ids(settings, workspace_id, service_id),
                {"tre_id": settings.tre_id, "tre_workspace_id": workspace_id, "tre_workspace_service_id": service_id},
                location,
                settings.tenant,
            )


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.databricks_validation
async def test_private_auth_lifecycle(verify):
    await validate_lifecycle(verify, workspace_service=False)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.databricks_validation
async def test_private_databricks_lifecycle(verify):
    await validate_lifecycle(verify, workspace_service=True)
