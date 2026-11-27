"""Invoke user resource actions and read the VM state that they change."""

from httpx import AsyncClient
from starlette import status

from e2e_tests.bundle_evidence import record_resource
from e2e_tests.helpers import assert_status, get_auth_header, get_full_endpoint
from e2e_tests.resources import strings
from e2e_tests.resources.deployment import check_deployment
from e2e_tests.resources.resource import TIMEOUT, wait_for
from e2e_tests.resources.sql_probe import COMPUTE_API

KEY_VAULT_API = "2023-07-01"
ACTION_TERMINAL = (strings.RESOURCE_ACTION_STATUS_SUCCEEDED, strings.RESOURCE_ACTION_STATUS_FAILED)


async def action_done(client, operation_endpoint, access_token):
    action_status, message, steps = await check_deployment(client, operation_endpoint, access_token)
    return action_status in ACTION_TERMINAL, action_status, message, steps


async def invoke_action(resource_path, action, access_token, verify):
    """Run one custom action and fail unless it succeeds."""
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        response = await client.post(
            get_full_endpoint(f"/api{resource_path}/invoke-action"),
            headers=get_auth_header(access_token),
            params={"action": action},
        )
        assert_status(response, [status.HTTP_202_ACCEPTED], f"The {action} action could not be sent")
        operation = response.json()["operation"]
        if operation["resourcePath"] != resource_path:
            raise ValueError("The action returned an operation for a different resource")
        record_resource(None, operation, "POST")
        await wait_for(
            action_done,
            client,
            response.headers["Location"],
            access_token,
            [strings.RESOURCE_ACTION_STATUS_FAILED],
        )


async def power_state(arm, vm_id):
    view = await arm.request("GET", f"{vm_id}/instanceView", COMPUTE_API)
    states = [s["code"] for s in view.get("statuses", []) if s.get("code", "").startswith("PowerState/")]
    if len(states) != 1:
        raise AssertionError("The VM reported no single power state")
    return states[0]


async def secret_version(arm, vault_id, secret_name):
    """Read the current secret version through ARM. The response contains no secret value."""
    secret = await arm.request("GET", f"{vault_id}/secrets/{secret_name}", KEY_VAULT_API)
    return secret["properties"]["secretUriWithVersion"].rsplit("/", 1)[1]
