import asyncio
import logging
from e2e_tests.bundle_evidence import record_resource, record_operation
from contextlib import asynccontextmanager
from e2e_tests.timeouts import cleanup_deadline
from httpx import AsyncClient, Timeout
from starlette import status
from e2e_tests.helpers import assert_status, get_auth_header, get_full_endpoint
from e2e_tests.resources.deployment import delete_done, install_done, patch_done

from resources import strings

LOGGER = logging.getLogger(__name__)
TIMEOUT = Timeout(10, read=60)
FAILED_CREATE_CLEANUP_TIMEOUT_SECONDS = 60 * 60


async def get_resource(endpoint, access_token, verify):
    async with AsyncClient(verify=verify, timeout=30.0) as client:
        full_endpoint = get_full_endpoint(endpoint)
        auth_headers = get_auth_header(access_token)

        response = await client.get(full_endpoint, headers=auth_headers, timeout=TIMEOUT)
        assert_status(response, [status.HTTP_200_OK], f"Failed to GET {full_endpoint}")

        return response.json()


async def post_resource(
    payload,
    endpoint,
    access_token,
    verify,
    method="POST",
    wait=True,
    etag="*",
    access_token_for_wait=None,
    *,
    cleanup_failed_create=False,
):
    if cleanup_failed_create and (method != "POST" or not wait):
        raise ValueError("Failed-create cleanup requires a POST with deployment polling")
    async with AsyncClient(verify=verify, timeout=30.0) as client:
        full_endpoint = get_full_endpoint(endpoint)
        auth_headers = get_auth_header(access_token)

        if method == "POST":
            response = await client.post(full_endpoint, headers=auth_headers, json=payload, timeout=TIMEOUT)
            check_method = install_done
        else:
            auth_headers["eTag"] = etag  # defaulted as * to force the update.
            check_method = patch_done
            response = await client.patch(full_endpoint, headers=auth_headers, json=payload, timeout=TIMEOUT)

        assert_status(response, [status.HTTP_202_ACCEPTED], "The resource couldn't be sent")

        record_resource(payload, response.json()["operation"], method)
        resource_path = response.json()["operation"]["resourcePath"]
        resource_id = response.json()["operation"]["resourceId"]
        operation_endpoint = response.headers["Location"]

        if wait:
            wait_token = access_token_for_wait if access_token_for_wait is not None else access_token
            try:
                await wait_for(
                    check_method,
                    client,
                    operation_endpoint,
                    wait_token,
                    [strings.RESOURCE_STATUS_DEPLOYMENT_FAILED, strings.RESOURCE_STATUS_UPDATING_FAILED],
                )
            except BaseException as original_error:
                if cleanup_failed_create:
                    cleanup = asyncio.create_task(
                        cleanup_accepted_create(resource_path, operation_endpoint, client, wait_token, verify)
                    )
                    # Cancellation must not abandon a known resource before its
                    # fixture can register teardown. Recovery has its own deadline.
                    while not cleanup.done():
                        try:
                            await asyncio.shield(cleanup)
                        except asyncio.CancelledError:
                            continue
                        except Exception:
                            break
                    try:
                        cleanup.result()
                    except BaseException as cleanup_error:
                        original_error.add_note(
                            f"Cleanup of {resource_path} after {operation_endpoint} also failed: {cleanup_error!r}"
                        )
                raise

        return resource_path, resource_id


async def cleanup_accepted_create(resource_path, operation_endpoint, client, access_token, verify):
    async with cleanup_deadline(FAILED_CREATE_CLEANUP_TIMEOUT_SECONDS):
        # An accepted deployment may still be running when its caller times out.
        # Wait for it to finish before sending another provisioning action.
        await wait_for(install_done, client, operation_endpoint, access_token, [])
        await disable_and_delete_resource(f"/api{resource_path}", access_token, verify, allow_failed_disable=True)


async def disable_and_delete_resource(endpoint, access_token, verify, *, allow_failed_disable=False):
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        full_endpoint = get_full_endpoint(endpoint)
        auth_headers = get_auth_header(access_token)
        auth_headers["etag"] = "*"  # for now, send in the wildcard to skip around etag checking

        # disable
        payload = {"isEnabled": False}
        response = await client.patch(full_endpoint, headers=auth_headers, json=payload, timeout=TIMEOUT)
        assert_status(response, [status.HTTP_202_ACCEPTED], "The resource couldn't be disabled")
        operation_endpoint = response.headers["Location"]
        # The API persists isEnabled=False before provisioning. Failed installs can
        # fail again during disable, but deletion is safe once that operation ends.
        failure_states = [] if allow_failed_disable else [strings.RESOURCE_STATUS_UPDATING_FAILED]
        disable_state = await wait_for(patch_done, client, operation_endpoint, access_token, failure_states)
        if disable_state == strings.RESOURCE_STATUS_UPDATING_FAILED:
            response = await client.get(full_endpoint, headers=get_auth_header(access_token), timeout=TIMEOUT)
            assert_status(response, [status.HTTP_200_OK], "Could not verify disabled resource")
            resources = [
                response.json()[key]
                for key in ("workspace", "workspaceService", "userResource", "sharedService")
                if key in response.json()
            ]
            assert len(resources) == 1 and resources[0].get("isEnabled") is False, (
                "Refusing deletion after failed disable: the resource is not confirmed disabled"
            )

        # delete
        auth_headers = get_auth_header(access_token)
        auth_headers["etag"] = "*"
        response = await client.delete(full_endpoint, headers=auth_headers, timeout=TIMEOUT)
        assert_status(response, [status.HTTP_200_OK], "The resource couldn't be deleted")

        resource_id = response.json()["operation"]["resourceId"]
        operation_endpoint = response.headers["Location"]

        await wait_for(delete_done, client, operation_endpoint, access_token, [strings.RESOURCE_STATUS_DELETING_FAILED])
        return resource_id


@asynccontextmanager
async def temporary_resource(payload, endpoint, access_token, verify):
    """Create a test resource and remove it after success or failed provisioning."""
    resource_path, _ = await post_resource(payload, endpoint, access_token, verify, cleanup_failed_create=True)
    try:
        yield resource_path
    except BaseException as original_error:
        try:
            async with cleanup_deadline(FAILED_CREATE_CLEANUP_TIMEOUT_SECONDS):
                await disable_and_delete_resource(
                    f"/api{resource_path}", access_token, verify, allow_failed_disable=True
                )
        except Exception as cleanup_error:
            original_error.add_note(f"Cleanup of {resource_path} also failed: {cleanup_error!r}")
        raise
    else:
        async with cleanup_deadline(FAILED_CREATE_CLEANUP_TIMEOUT_SECONDS):
            await disable_and_delete_resource(f"/api{resource_path}", access_token, verify)


async def wait_for(func, client, operation_endpoint, access_token, failure_states: list):
    done_state, message, operation_steps = "not yet observed", "", ""
    LOGGER.info(f"WAITING FOR OP: {operation_endpoint}")
    try:
        done, done_state, message, operation_steps = await func(client, operation_endpoint, access_token)
        record_operation(operation_endpoint, done_state, done)
        while not done:
            await asyncio.sleep(30)

            done, done_state, message, operation_steps = await func(client, operation_endpoint, access_token)
            record_operation(operation_endpoint, done_state, done)
            LOGGER.info(f"{done}, {done_state}, {message}")
    except asyncio.CancelledError:
        LOGGER.error(
            "Stopped waiting for operation %s. Last observed state: %s; message: %s; steps: %s",
            operation_endpoint,
            done_state,
            message,
            operation_steps,
        )
        raise
    try:
        assert done_state not in failure_states
    except Exception:
        LOGGER.exception(f"Failed to deploy. Status message: {message}.\n{operation_steps}")
        raise
    return done_state


async def delete_owned_resource_if_present(resource_path, access_token, verify):
    """Wait for active operations and remove an owned resource, unless already deleted."""
    terminal = {
        "deployed",
        "deployment_failed",
        "updated",
        "updating_failed",
        "deleted",
        "deleting_failed",
        "action_succeeded",
        "action_failed",
        "pipeline_succeeded",
        "pipeline_failed",
    }
    endpoint = get_full_endpoint(f"/api{resource_path}")
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        while True:
            response = await client.get(endpoint, headers=get_auth_header(access_token), timeout=TIMEOUT)
            if response.status_code == 404:
                return
            assert_status(response, [status.HTTP_200_OK], "Could not inspect the owned review VM")
            state = response.json()["userResource"]["deploymentStatus"]
            if state == "deleted":
                return
            operations = await client.get(
                endpoint + "/operations", headers=get_auth_header(access_token), timeout=TIMEOUT
            )
            if operations.status_code == 404:
                return
            assert_status(operations, [status.HTTP_200_OK], "Could not inspect review VM operations")
            if state in terminal and all(op["status"] in terminal for op in operations.json()["operations"]):
                break
            await asyncio.sleep(30)
    await disable_and_delete_resource(f"/api{resource_path}", access_token, verify, allow_failed_disable=True)
