"""Validate private OpenAI deployment after checking model and quota prerequisites."""

import asyncio
import os
import re

import pytest
from httpx import AsyncClient

from e2e_tests import config
from e2e_tests.conftest import get_workspace_owner_token
from e2e_tests.helpers import TIMEOUT, get_auth_header, get_full_endpoint
from e2e_tests.resources import strings
from e2e_tests.resources.openai import CAPACITY, COGNITIVE_API, MODEL, check_prerequisites
from e2e_tests.resources.resource import get_resource, temporary_resource
from e2e_tests.resources.sql_probe import arm_client

CREATE_TIMEOUT_SECONDS = 45 * 60
VERIFY_TIMEOUT_SECONDS = 5 * 60


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.workspace_services
@pytest.mark.openai_validation
async def test_private_openai_lifecycle(verify, setup_test_workspace):
    if os.environ.get("AZURE_ENVIRONMENT", "AzureCloud") != "AzureCloud":
        raise ValueError("The OpenAI prerequisite check currently supports AzureCloud only")
    workspace_path, workspace_id = setup_test_workspace
    token = await get_workspace_owner_token(workspace_id, verify)
    async with arm_client() as arm:
        async with asyncio.timeout(5 * 60):
            workspace = (await get_resource(f"/api{workspace_path}", token, verify))["workspace"]
            subscription = os.environ["ARM_SUBSCRIPTION_ID"]
            if (
                workspace["properties"].get("workspace_subscription_id") or subscription
            ).lower() != subscription.lower():
                raise ValueError("This OpenAI bundle requires the workspace and core in the same subscription")
            if not re.fullmatch(r"[a-fA-F0-9-]{36}", subscription) or not re.fullmatch(r"[a-z0-9-]+", config.TRE_ID):
                raise ValueError("Invalid subscription or TRE identifier for the OpenAI prerequisite check")
            group = f"/subscriptions/{subscription}/resourceGroups/rg-{config.TRE_ID}-ws-{workspace_id[-4:]}"
            region = (await arm.request("GET", group, "2022-09-01"))["location"]
            if not re.fullmatch(r"[a-z0-9]+", region):
                raise ValueError("Invalid workspace region for the OpenAI prerequisite check")
            await check_prerequisites(arm, subscription, region)
        payload = {
            "templateName": strings.OPENAI_SERVICE,
            "properties": {
                "display_name": "Private OpenAI lifecycle test",
                "description": "OpenAI deployment and cleanup validation",
                "openai_model": MODEL,
                "is_exposed_externally": False,
            },
        }
        # Cancel the creation deadline after deployment. Verification and cleanup
        # each have their own budget, even if creation uses its full allowance.
        async with asyncio.timeout(CREATE_TIMEOUT_SECONDS) as creation_deadline:
            async with temporary_resource(
                payload, f"/api{workspace_path}/workspace-services", token, verify
            ) as service_path:
                creation_deadline.reschedule(None)
                async with asyncio.timeout(VERIFY_TIMEOUT_SECONDS):
                    service = (await get_resource(f"/api{service_path}", token, verify))["workspaceService"]
                    assert service["templateName"] == strings.OPENAI_SERVICE
                    assert service["deploymentStatus"] == strings.RESOURCE_STATUS_DEPLOYED
                    properties = service["properties"]
                    assert properties["openai_model"] == MODEL
                    assert properties["is_exposed_externally"] is False
                    account_name = f"openai-{config.TRE_ID}-ws-{workspace_id[-4:]}-svc-{service['id'][-4:]}"
                    account_id = f"{group}/providers/Microsoft.CognitiveServices/accounts/{account_name}"
                    account = await arm.request("GET", account_id, COGNITIVE_API)
                    assert account["properties"]["provisioningState"] == "Succeeded"
                    assert account["properties"]["publicNetworkAccess"] == "Disabled"
                    assert properties["openai_fqdn"] == account["properties"]["endpoint"]
                    name, version = (part.strip() for part in MODEL.split("|"))
                    deployment_name = (
                        f"openai-{name}-{version}-{config.TRE_ID}-ws-{workspace_id[-4:]}-svc-{service['id'][-4:]}"
                    )
                    assert properties["openai_deployment_id"] == deployment_name
                    deployment = await arm.request("GET", f"{account_id}/deployments/{deployment_name}", COGNITIVE_API)
                    assert deployment["properties"]["provisioningState"] == "Succeeded"
                    model = deployment["properties"]["model"]
                    assert (model["format"], model["name"], model["version"]) == ("OpenAI", name, version)
                    assert deployment["sku"]["name"] == "Standard"
                    assert deployment["sku"]["capacity"] == CAPACITY
        async with asyncio.timeout(5 * 60):
            async with AsyncClient(verify=verify) as client:
                response = await client.get(
                    get_full_endpoint(f"/api{service_path}"), headers=get_auth_header(token), timeout=TIMEOUT
                )
            assert response.status_code == 404, f"OpenAI service remains visible: HTTP {response.status_code}"
            assert await arm.request("GET", account_id, COGNITIVE_API, missing_ok=True) is None, (
                "OpenAI account remains active after uninstall"
            )
