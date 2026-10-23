"""Exercise private FHIR access, access control and a DICOM update."""

import asyncio
from functools import partial
import logging
import os
from uuid import uuid4

import pytest

from e2e_tests import config
from e2e_tests.conftest import get_workspace_owner_token
from e2e_tests.resources import strings
from e2e_tests.resources.health_probe import FHIR_DATA_CONTRIBUTOR, role_access, run_probe
from e2e_tests.resources.resource import get_resource, post_resource
from e2e_tests.resources.sql_lifecycle import sql_lifecycle
from e2e_tests.resources.sql_probe import arm_client, COMPUTE_API, validate_vm

LOGGER = logging.getLogger(__name__)
HEALTH_API = "2024-03-31"
HEALTH_PAYLOAD = {
    "templateName": strings.HEALTH_SERVICE,
    "properties": {
        "display_name": "Health lifecycle test",
        "description": "Private FHIR and DICOM validation",
        "deploy_fhir": True,
        "fhir_kind": "R4",
        "deploy_dicom": False,
    },
}
VM_PAYLOAD = {
    "templateName": strings.GUACAMOLE_WINDOWS_USER_RESOURCE,
    "properties": {
        "display_name": "Health test client",
        "description": "Temporary private FHIR validation client",
        "os_image": "Windows 11",
        "vm_size": "2 CPU | 8GB RAM",
        "admin_username": "researcher",
        "shared_storage_access": False,
        **{
            f"install_{tool}": False
            for tool in ("azure_cli", "vscode", "storage_explorer", "git", "python_tools", "r_tools")
        },
    },
}


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.health_validation
@pytest.mark.timeout(285 * 60)
async def test_private_fhir_access_and_dicom_update(verify):
    if os.environ.get("AZURE_ENVIRONMENT", "AzureCloud") != "AzureCloud":
        raise ValueError("The health probe currently supports AzureCloud only")
    async with sql_lifecycle(verify, deadline_variable="HEALTH_VALIDATION_DEADLINE") as resources:
        # The bundle refuses to install without the workspace owners group.
        workspace_path, workspace_id, guacamole_path, guacamole_id = await resources.setup(groups=True)
        new_token = partial(get_workspace_owner_token, workspace_id, verify)
        workspace = (await get_resource(f"/api{workspace_path}", await new_token(), verify))["workspace"]
        assert workspace["properties"].get("workspace_owners_group_id"), "The workspace has no owners group"
        health_path, health_id = await resources.create(
            HEALTH_PAYLOAD, f"/api{workspace_path}/workspace-services", await new_token(), cleanup_token=new_token
        )
        vm_path, vm_id = await resources.create(
            VM_PAYLOAD, f"/api{guacamole_path}/user-resources", await new_token(), cleanup_token=new_token
        )
        token = await new_token()
        health = (await get_resource(f"/api{health_path}", token, verify))["workspaceService"]
        vm_properties = (await get_resource(f"/api{vm_path}", token, verify))["userResource"]["properties"]
        subscription_id = vm_properties.get("workspace_subscription_id") or os.environ["ARM_SUBSCRIPTION_ID"]
        suffix = f"{workspace_id[-4:]}svc{health_id[-4:]}"
        fhir_url = f"https://hs{suffix}-fhir{suffix}.fhir.azurehealthcareapis.com"
        dicom_url = f"https://hs{suffix}-dicom{suffix}.dicom.azurehealthcareapis.com"
        assert health["properties"]["fhir_url"] == fhir_url
        assert not health["properties"].get("dicom_url")
        azure_vm_id = vm_properties["azure_resource_id"]
        async with arm_client() as arm:
            vm = await arm.request("GET", azure_vm_id, COMPUTE_API)
            group = validate_vm(vm, azure_vm_id, subscription_id, config.TRE_ID, workspace_id, guacamole_id, vm_id)
            workspace_arm_id = f"{group}/providers/Microsoft.HealthcareApis/workspaces/hs{suffix}"
            fhir_id = f"{workspace_arm_id}/fhirservices/fhir{suffix}"
            fhir = await arm.request("GET", fhir_id, HEALTH_API)
            assert fhir["properties"]["provisioningState"] == "Succeeded"
            probe_id = uuid4().hex
            probe = partial(run_probe, arm, azure_vm_id, vm["location"], fhir_url=fhir_url, probe_id=probe_id)
            await probe(phase="access")
            LOGGER.info("FHIR metadata is private, and data requests need a token and a role")
            async with role_access(arm, fhir_id, FHIR_DATA_CONTRIBUTOR, vm["identity"]["principalId"], subscription_id):
                await probe(phase="write")
                token = await new_token()
                health = (await get_resource(f"/api{health_path}", token, verify))["workspaceService"]
                async with asyncio.timeout(60 * 60):
                    await post_resource(
                        {"properties": {"deploy_dicom": True}},
                        f"/api{health_path}",
                        token,
                        verify,
                        method="PATCH",
                        etag=health["_etag"],
                    )
                health = (await get_resource(f"/api{health_path}", await new_token(), verify))["workspaceService"]
                assert health["properties"]["dicom_url"] == dicom_url
                dicom = await arm.request("GET", f"{workspace_arm_id}/dicomservices/dicom{suffix}", HEALTH_API)
                assert dicom["properties"]["provisioningState"] == "Succeeded"
                await probe(phase="read", dicom_url=dicom_url)
                LOGGER.info("FHIR data survived the update that added DICOM")
            # Check the network settings last, so that a failure here keeps the functional evidence above.
            workspace_record = await arm.request("GET", workspace_arm_id, HEALTH_API)
            network = {
                "workspace": workspace_record["properties"].get("publicNetworkAccess"),
                "fhir": fhir["properties"].get("publicNetworkAccess"),
                "dicom": dicom["properties"].get("publicNetworkAccess"),
            }
            LOGGER.info("Health public network access: %s", network)
            assert network == dict.fromkeys(network, "Disabled"), f"Health services allow public access: {network}"
