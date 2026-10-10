"""Validate one CycleCloud server without configuring or creating HPC clusters."""

from uuid import uuid4

import pytest

from e2e_tests.bundle_evidence import record_deployed_resource, record_reused_resource
from e2e_tests.helpers import get_admin_token
from e2e_tests.resources.cyclecloud import (
    COMPUTE_API,
    FIREWALL,
    TEMPLATE,
    assert_removed,
    firewall_rules,
    guard_owned,
    preflight,
    require_settings,
    resource_ids,
    uuid_value,
    validate_firewall,
    validate_resources,
    wait_power,
)
from e2e_tests.resources.cyclecloud_lifecycle import cyclecloud_lifecycle
from e2e_tests.resources.resource import get_resource
from e2e_tests.resources.sql_probe import arm_client
from e2e_tests.run_bundle import load_catalog


async def prerequisites(verify):
    catalog = load_catalog()
    token = await get_admin_token(verify)
    for name in (TEMPLATE, FIREWALL):
        template = await get_resource(f"/api/shared-service-templates/{name}", token, verify)
        if template["name"] != name or template["version"] != catalog[name]["source_version"]:
            raise ValueError(f"Register the checkout version of {name} before CycleCloud validation")
        if name == TEMPLATE and not {"start", "stop"} <= {a["name"] for a in template.get("customActions", [])}:
            raise ValueError("The registered CycleCloud template must expose start and stop")
    services = (await get_resource("/api/shared-services", token, verify))["sharedServices"]
    if any(s["templateName"] == TEMPLATE for s in services):
        raise ValueError("An existing CycleCloud service prevents isolated validation")
    firewalls = [s for s in services if s["templateName"] == FIREWALL]
    if len(firewalls) != 1:
        raise ValueError("CycleCloud requires exactly one deployed firewall")
    firewall = firewalls[0]
    if (
        firewall["isEnabled"] is not True
        or firewall["deploymentStatus"] not in ("deployed", "updated")
        or firewall["templateVersion"] != catalog[FIREWALL]["source_version"]
    ):
        raise ValueError("Deploy and enable the checkout firewall version before CycleCloud validation")
    record_reused_resource(firewall)
    return firewall


async def validate_lifecycle(verify):
    settings = require_settings()
    payload = {
        "templateName": TEMPLATE,
        "properties": {
            "display_name": f"CycleCloud validation {uuid4()}",
            "description": "Owned CycleCloud lifecycle validation",
        },
    }
    core = None
    baseline = None
    firewall = None
    principal = None

    async with arm_client() as arm:

        async def current_firewall():
            record = (
                await get_resource(f"/api/shared-services/{firewall['id']}", await get_admin_token(verify), verify)
            )["sharedService"]
            if record["id"] != firewall["id"] or record["templateName"] != FIREWALL:
                raise ValueError("CycleCloud firewall prerequisite identity changed")
            return record

        async def before_remove(identifier):
            nonlocal principal
            ids = resource_ids(settings, core, identifier)
            await guard_owned(arm, ids, {"tre_id": settings.tre_id, "tre_shared_service_id": identifier})
            vm = await arm.request("GET", ids["vm"], COMPUTE_API, missing_ok=True)
            if vm is not None and vm.get("identity", {}).get("principalId"):
                principal = uuid_value(vm["identity"]["principalId"])

        async def after_remove(identifier):
            await assert_removed(arm, resource_ids(settings, core, identifier), settings.subscription, principal)
            assert firewall_rules(await current_firewall()) == baseline, "CycleCloud firewall rules were not restored"

        async with cyclecloud_lifecycle(verify, payload, before_remove, after_remove) as service:
            firewall = await prerequisites(verify)
            baseline = firewall_rules(firewall)
            core = await preflight(arm, settings)
            record = await service.create()
            ids = resource_ids(settings, core, service.identifier)

            async def inspect(record):
                assert record["templateVersion"] == load_catalog()[TEMPLATE]["source_version"]
                assert record["properties"]["connection_uri"] == "https://" + core["zone"].rsplit("/", 1)[1]
                record_deployed_resource(record, service.path)
                identity = await validate_resources(arm, settings, core, ids, service.identifier)
                validate_firewall(await current_firewall(), baseline, service.identifier, core["prefixes"])
                return identity

            principal = await inspect(record)
            await wait_power(arm, ids["vm"], "running")
            await service.change(action="stop")
            await wait_power(arm, ids["vm"], "deallocated")
            await service.change(action="start")
            await wait_power(arm, ids["vm"], "running")
            updated = await service.change(overview="CycleCloud lifecycle metadata upgrade")
            assert await inspect(updated) == principal, "CycleCloud upgrade replaced the VM identity"


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.cyclecloud_validation
async def test_cyclecloud_lifecycle(verify):
    await validate_lifecycle(verify)
