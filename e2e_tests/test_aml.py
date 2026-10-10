"""Validate private AML resources through TRE and ARM lifecycle observations."""

import pytest

from e2e_tests import config
from e2e_tests.bundle_evidence import record_deployed_resource
from e2e_tests.conftest import get_workspace_owner_token
from e2e_tests.helpers import get_admin_token
from e2e_tests.resources import strings
from e2e_tests.resources.aml import (
    AML_API,
    COMPUTE_TEMPLATE,
    VM_SIZE,
    require_prerequisites,
    resource_ids,
    uuid_value,
    validate_service,
    wait_for_compute,
)
from e2e_tests.resources.aml_lifecycle import aml_lifecycle
from e2e_tests.resources.resource import get_resource
from e2e_tests.resources.sql_probe import arm_client
from e2e_tests.run_bundle import load_catalog

SERVICE_PAYLOAD = {
    "templateName": strings.AZUREML_SERVICE,
    "properties": {
        "display_name": "Private AML lifecycle test",
        "description": "Private Azure Machine Learning deployment and cleanup validation",
        "is_exposed_externally": False,
    },
}


async def deployed_resource(resource_path, resource_key, template, workspace_id, verify):
    token = await get_workspace_owner_token(workspace_id, verify)
    resource = (await get_resource(f"/api{resource_path}", token, verify))[resource_key]
    assert resource["id"] == resource_path.rsplit("/", 1)[1]
    assert resource["templateName"] == template
    assert resource["deploymentStatus"] == "deployed"
    record_deployed_resource(resource, resource_path)
    assert resource["templateVersion"] == load_catalog()[template]["source_version"], (
        "The deployed AML dependency bundle version differs from this checkout"
    )
    return resource


def validate_workspace(workspace, subscription):
    properties = workspace["properties"]
    assert properties["auth_type"] == "Automatic", "AML validation requires an Automatic workspace"
    configured_subscription = properties.get("workspace_subscription_id") or subscription
    if configured_subscription.lower() != subscription.lower():
        raise ValueError("AML validation requires the workspace and core in the same subscription")
    for name in ("workspace_owners_group_id", "workspace_researchers_group_id"):
        uuid_value(properties.get(name, ""), name)


async def require_templates(verify, *, compute):
    catalog = load_catalog()
    parent_endpoint = f"{strings.API_WORKSPACE_SERVICE_TEMPLATES}/{strings.AZUREML_SERVICE}"
    templates = [
        (strings.BASE_WORKSPACE, f"{strings.API_WORKSPACE_TEMPLATES}/{strings.BASE_WORKSPACE}"),
        (strings.AZUREML_SERVICE, parent_endpoint),
    ]
    if compute:
        templates.append((COMPUTE_TEMPLATE, f"{parent_endpoint}/user-resource-templates/{COMPUTE_TEMPLATE}"))
    token = await get_admin_token(verify)
    for name, endpoint in templates:
        template = await get_resource(endpoint, token, verify)
        assert template["name"] == name, "The registered AML prerequisite template has a different name"
        assert template["version"] == catalog[name]["source_version"], (
            f"Register the checkout version of {name} before AML validation"
        )


async def validate_lifecycle(verify, *, compute):
    # Fail before creating any resource when operator configuration is missing.
    subscription, tenant, user_id = require_prerequisites(compute=compute)
    async with arm_client() as arm:
        async with aml_lifecycle(verify) as resources:
            await require_templates(verify, compute=compute)
            workspace_path, workspace_id = await resources.workspace()
            workspace = await deployed_resource(
                workspace_path, "workspace", strings.BASE_WORKSPACE, workspace_id, verify
            )
            validate_workspace(workspace, subscription)
            service_path, service_id = await resources.create(
                SERVICE_PAYLOAD, f"/api{workspace_path}/workspace-services", workspace_id
            )
            group, aml_id, subnet_id, _ = resource_ids(subscription, config.TRE_ID, workspace_id, service_id)
            resources.track_arm(service_path, arm, aml_id)
            service = await deployed_resource(
                service_path, "workspaceService", strings.AZUREML_SERVICE, workspace_id, verify
            )
            assert service["properties"]["is_exposed_externally"] is False
            assert service["properties"]["azureml_workspace_name"] == aml_id.rsplit("/", 1)[1]
            group_record = await arm.request("GET", group, "2022-09-01")
            assert group_record["id"].lower() == group.lower()
            tags = {"tre_id": config.TRE_ID, "tre_workspace_id": workspace_id, "tre_workspace_service_id": service_id}
            validate_service(await arm.request("GET", aml_id, AML_API), aml_id, tags)
            if compute:
                payload = {
                    "templateName": COMPUTE_TEMPLATE,
                    "properties": {
                        "display_name": "Private AML compute lifecycle test",
                        "description": "Private compute provisioning, state and cleanup validation",
                        "vm_size": VM_SIZE,
                        "user_object_id": user_id,
                    },
                }
                compute_path, compute_id = await resources.create(
                    payload, f"/api{service_path}/user-resources", workspace_id
                )
                _, _, _, arm_compute_id = resource_ids(
                    subscription, config.TRE_ID, workspace_id, service_id, compute_id
                )
                resources.track_arm(compute_path, arm, arm_compute_id)
                record = await deployed_resource(compute_path, "userResource", COMPUTE_TEMPLATE, workspace_id, verify)
                assert record["properties"]["vm_size"] == VM_SIZE
                assert record["properties"]["user_object_id"].lower() == user_id.lower()
                await wait_for_compute(
                    arm, arm_compute_id, subnet_id, {**tags, "tre_user_resource_id": compute_id}, tenant, user_id
                )


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.aml_validation
async def test_private_aml_service_lifecycle(verify):
    await validate_lifecycle(verify, compute=False)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.aml_validation
async def test_private_aml_compute_lifecycle(verify):
    await validate_lifecycle(verify, compute=True)
