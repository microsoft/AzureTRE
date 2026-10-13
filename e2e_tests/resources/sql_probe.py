"""Run a private SQL probe from a test-created workspace VM."""

import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import re
from urllib.parse import urlparse
from uuid import uuid4

from azure.identity import AzureCliCredential, ClientAssertionCredential
from httpx import AsyncClient
import requests

from e2e_tests.timeouts import cleanup_deadline


ARM = "https://management.azure.com"
SECRETS_USER = "4633458b-17de-408a-b874-0445c86b69e6"
COMPUTE_API = "2023-03-01"
ROLE_API = "2022-04-01"
SCRIPT = Path(__file__).with_name("sql_probe.ps1")


class ArmClient:
    """Use CI's existing CLI login without exposing response bodies on errors."""

    def __init__(self, client, credential):
        self.client = client
        self.credential = credential

    async def request(self, method, resource_id, api_version, *, body=None, missing_ok=False, expand=False):
        if not resource_id.startswith("/subscriptions/") or any(c in resource_id for c in "?#"):
            raise ValueError("Expected an ARM resource ID")
        token = await asyncio.to_thread(self.credential.get_token, f"{ARM}/.default")
        params = {"api-version": api_version}
        if expand:
            params["$expand"] = "instanceView"
        response = await self.client.request(
            method,
            f"{ARM}{resource_id}",
            params=params,
            headers={"Authorization": f"Bearer {token.token}"},
            json=body,
        )
        if missing_ok and response.status_code == 404:
            return None
        if response.status_code not in (200, 201, 202, 204):
            raise RuntimeError(f"ARM {method} {resource_id} failed with HTTP {response.status_code}")
        return response.json() if response.content else {}

    async def delete(self, resource_id, api_version):
        async with asyncio.timeout(180):
            await self.request("DELETE", resource_id, api_version, missing_ok=True)
            while await self.request("GET", resource_id, api_version, missing_ok=True) is not None:
                await asyncio.sleep(5)


@asynccontextmanager
async def arm_client():
    # Long deployments can outlive azure/login's cached token. Request a fresh
    # GitHub assertion when Azure Identity needs to renew the ARM token.
    if os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL"):
        credential = ClientAssertionCredential(
            os.environ["ARM_TENANT_ID"], os.environ["ARM_CLIENT_ID"], github_assertion
        )
    else:
        credential = AzureCliCredential()
    with credential:
        async with AsyncClient(timeout=60) as client:
            yield ArmClient(client, credential)


def github_assertion():
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    parsed = urlparse(url)
    if parsed.scheme != "https" or not (parsed.hostname or "").endswith(".actions.githubusercontent.com"):
        raise ValueError("Unexpected GitHub OIDC endpoint")
    response = requests.get(
        url,
        params={"audience": "api://AzureADTokenExchange"},
        headers={"Authorization": f"Bearer {os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']}"},
        timeout=30,
        allow_redirects=False,
    )
    if response.status_code != 200:
        raise RuntimeError(f"GitHub OIDC request failed with HTTP {response.status_code}")
    return response.json()["value"]


def validate_vm(vm, vm_id, subscription_id, tre_id, workspace_id, service_id, resource_id):
    expected = {
        "tre_id": tre_id,
        "tre_workspace_id": workspace_id,
        "tre_workspace_service_id": service_id,
        "tre_user_resource_id": resource_id,
    }
    group = f"/subscriptions/{subscription_id}/resourceGroups/rg-{tre_id}-ws-{workspace_id[-4:]}"
    if not re.fullmatch(re.escape(group) + r"/providers/Microsoft.Compute/virtualMachines/[a-zA-Z0-9-]+", vm_id, re.I):
        raise ValueError("SQL probe VM is outside the expected workspace")
    if vm.get("id", "").lower() != vm_id.lower() or any(vm.get("tags", {}).get(k) != v for k, v in expected.items()):
        raise ValueError("SQL probe VM does not match the test-created resource")
    if not vm.get("identity", {}).get("principalId"):
        raise ValueError("SQL probe VM has no system-assigned identity")
    return group


@asynccontextmanager
async def delete_after(arm, resource_id, api_version):
    """Finish bounded probe cleanup before propagating caller cancellation."""
    original = None
    try:
        yield
    except BaseException as error:
        original = error
        raise
    finally:

        async def remove():
            async with cleanup_deadline(180):
                await arm.delete(resource_id, api_version)

        cleanup = asyncio.create_task(remove())
        cancelled = None
        while not cleanup.done():
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError as error:
                cancelled = error
            except Exception:
                break
        try:
            cleanup.result()
        except (Exception, asyncio.CancelledError) as error:
            failure = original or cancelled
            if failure is None:
                raise
            failure.add_note(f"Cleanup of {resource_id} also failed: {error!r}")
        if original is None and cancelled is not None:
            raise cancelled


@asynccontextmanager
async def secret_access(arm, vault_id, secret_name, principal_id, subscription_id):
    """Grant only this VM access to this SQL secret, then verify revocation."""
    assignment = f"{vault_id}/secrets/{secret_name}/providers/Microsoft.Authorization/roleAssignments/{uuid4()}"
    body = {
        "properties": {
            "roleDefinitionId": f"/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/{SECRETS_USER}",
            "principalId": principal_id,
            "principalType": "ServicePrincipal",
        }
    }
    # The PUT may have succeeded even if its response was lost.
    async with delete_after(arm, assignment, ROLE_API):
        await arm.request("PUT", assignment, ROLE_API, body=body)
        yield


def probe_result(resource, phase, probe_id, expected_sku):
    properties = resource.get("properties", {})
    view = properties.get("instanceView", {})
    state = view.get("executionState", "")
    if properties.get("provisioningState") in ("Failed", "Canceled") or state in ("Failed", "Canceled", "TimedOut"):
        raise AssertionError(f"SQL probe failed: state={state}, exitCode={view.get('exitCode')}")
    if state != "Succeeded":
        return False
    if view.get("exitCode") != 0:
        raise AssertionError("SQL probe returned a non-zero exit code")
    marker = "SQL_PROBE_RESULT="
    results = [line[len(marker) :] for line in view.get("output", "").splitlines() if line.startswith(marker)]
    expected = {"phase": phase, "probe": probe_id, "sku": expected_sku, "row_count": 1, "private_dns": True}
    if len(results) != 1 or json.loads(results[0]) != expected:
        raise AssertionError("SQL probe did not confirm the expected data, SKU and private DNS")
    return True


async def run_probe(arm, vm_id, location, *, server, vault_name, secret_name, probe_id, phase, expected_sku):
    parameters = {
        "Server": server,
        "VaultName": vault_name,
        "SecretName": secret_name,
        "ProbeId": probe_id,
        "Phase": phase,
        "ExpectedSku": expected_sku,
    }
    command = f"{vm_id}/runCommands/sql-probe-{uuid4().hex}"
    # Removing our command also terminates it if its deadline expired.
    async with delete_after(arm, command, COMPUTE_API):
        async with asyncio.timeout(15 * 60):
            await arm.request(
                "PUT",
                command,
                COMPUTE_API,
                body={
                    "location": location,
                    "properties": {
                        "source": {"script": SCRIPT.read_text()},
                        "parameters": [{"name": k, "value": v} for k, v in parameters.items()],
                        "timeoutInSeconds": 600,
                        "treatFailureAsDeploymentFailure": True,
                    },
                },
            )
            while True:
                result = await arm.request("GET", command, COMPUTE_API, expand=True)
                if probe_result(result, phase, probe_id, expected_sku):
                    return
                await asyncio.sleep(10)
