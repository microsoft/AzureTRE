"""Inspect AML resources without changing identities or network access."""

import asyncio
import os
import re
from uuid import UUID

from e2e_tests import config

AML_API = "2024-04-01"
VM_SIZE = "Standard_D2_v3"
COMPUTE_TEMPLATE = "tre-user-resource-aml-compute-instance"


def uuid_value(value, name):
    try:
        parsed = UUID(value)
        if not parsed.int or str(parsed) != value.lower():
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"AML validation requires a non-zero UUID for {name}") from None
    return str(parsed)


def require_prerequisites(compute=False):
    """Check configuration before provisioning without querying the directory."""
    if os.environ.get("AZURE_ENVIRONMENT", "AzureCloud") != "AzureCloud":
        raise ValueError("AML validation currently supports AzureCloud only")
    subscription = uuid_value(os.environ.get("ARM_SUBSCRIPTION_ID", ""), "ARM_SUBSCRIPTION_ID")
    tenant = uuid_value(os.environ.get("ARM_TENANT_ID", ""), "ARM_TENANT_ID")
    if uuid_value(config.AAD_TENANT_ID, "AAD_TENANT_ID") != tenant:
        raise ValueError("AML validation requires the authentication and Azure tenants to match")
    if not re.fullmatch(r"[a-z0-9-]+", config.TRE_ID):
        raise ValueError("AML validation requires a valid TRE_ID")
    user = uuid_value(os.environ.get("TEST_AML_USER_OBJECT_ID", ""), "TEST_AML_USER_OBJECT_ID") if compute else ""
    return subscription, tenant, user


def resource_ids(subscription, tre_id, workspace_id, service_id, resource_id=None):
    """Use the bundle's naming contract, with validated path components."""
    subscription = uuid_value(subscription, "subscription")
    workspace_id = uuid_value(workspace_id, "workspace")
    service_id = uuid_value(service_id, "service")
    if not re.fullmatch(r"[a-z0-9-]+", tre_id):
        raise ValueError("Invalid TRE identifier for AML resources")
    suffix = f"{tre_id}-ws-{workspace_id[-4:]}"
    service_suffix = f"{suffix}-svc-{service_id[-4:]}"
    group = f"/subscriptions/{subscription}/resourceGroups/rg-{suffix}"
    workspace = f"{group}/providers/Microsoft.MachineLearningServices/workspaces/ml-{service_suffix[-30:]}"
    subnet = f"{group}/providers/Microsoft.Network/virtualNetworks/vnet-{suffix}/subnets/AMLSubnet{service_id[-4:]}"
    compute = None
    if resource_id is not None:
        resource_id = uuid_value(resource_id, "compute resource")
        compute = f"{workspace}/computes/ci-{service_id[-4:]}{resource_id[-4:]}"
    return group, workspace, subnet, compute


def validate_ownership(resource, arm_id, tags):
    if resource.get("id", "").lower() != arm_id.lower():
        raise AssertionError("AML response does not match the test-created resource")
    if any(resource.get("tags", {}).get(key) != value for key, value in tags.items()):
        raise AssertionError("AML ownership tags do not match the test-created resource")


def validate_service(resource, arm_id, tags):
    validate_ownership(resource, arm_id, tags)
    properties = resource["properties"]
    assert properties["provisioningState"] == "Succeeded", "AML workspace provisioning did not succeed"
    assert properties["publicNetworkAccess"] == "Disabled", "AML workspace permits public access"


def validate_compute(resource, arm_id, subnet_id, tags, tenant, user):
    validate_ownership(resource, arm_id, tags)
    properties = resource["properties"]
    assert properties["computeType"] == "ComputeInstance", "Unexpected AML compute type"
    state = properties["provisioningState"]
    assert state not in ("Failed", "Canceled"), f"AML compute provisioning failed: {state}"
    details = properties["properties"]
    assert details["vmSize"].lower() == VM_SIZE.lower(), "Unexpected AML compute size"
    assert details["enableNodePublicIp"] is False, "AML compute permits a node public IP"
    assert details["subnet"]["id"].lower() == subnet_id.lower(), "AML compute is outside the expected subnet"
    assert details["computeInstanceAuthorizationType"] == "personal", "Unexpected AML compute authorisation"
    assigned = details["personalComputeInstanceSettings"]["assignedUser"]
    assert assigned["objectId"].lower() == user.lower(), "AML compute has a different assigned user"
    assert assigned["tenantId"].lower() == tenant.lower(), "AML compute has a different assigned tenant"
    assert not details.get("connectivityEndpoints", {}).get("publicIpAddress"), "AML compute has a public IP"
    compute_state = details["state"]
    assert compute_state not in ("Failed", "Unusable", "JobFailed", "CreateFailed", "SetupFailed", "UserSetupFailed"), (
        f"AML compute failed: {compute_state}"
    )
    return state == "Succeeded" and compute_state == "Running"


async def wait_for_compute(arm, arm_id, subnet_id, tags, tenant, user):
    async with asyncio.timeout(20 * 60):
        while True:
            resource = await arm.request("GET", arm_id, AML_API)
            if validate_compute(resource, arm_id, subnet_id, tags, tenant, user):
                return resource
            await asyncio.sleep(20)


async def assert_removed(arm, arm_id):
    async with asyncio.timeout(5 * 60):
        while await arm.request("GET", arm_id, AML_API, missing_ok=True) is not None:
            await asyncio.sleep(10)
