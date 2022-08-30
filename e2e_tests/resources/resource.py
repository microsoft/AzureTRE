import asyncio
import logging
from httpx import AsyncClient, Timeout
from starlette import status
from e2e_tests.helpers import get_auth_header, get_full_endpoint
from e2e_tests.resources.deployment import delete_done, install_done, patch_done

from resources import strings

LOGGER = logging.getLogger(__name__)
TIMEOUT = Timeout(10, read=30)


async def post_resource(payload, endpoint, access_token, verify, method="POST", wait=True, etag="*"):
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

        LOGGER.info(f'RESPONSE Status code: {response.status_code} Content: {response.content}')
        assert (response.status_code == status.HTTP_202_ACCEPTED), f"Request for resource {payload['templateName']} creation failed"

        resource_path = response.json()["operation"]["resourcePath"]
        resource_id = response.json()["operation"]["resourceId"]
        operation_endpoint = response.headers["Location"]

        if wait:
            await wait_for(check_method, client, operation_endpoint, auth_headers, [strings.RESOURCE_STATUS_DEPLOYMENT_FAILED, strings.RESOURCE_STATUS_UPDATING_FAILED])

        return resource_path, resource_id


async def disable_and_delete_resource(endpoint, access_token, verify):
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:

        full_endpoint = get_full_endpoint(endpoint)
        auth_headers = get_auth_header(access_token)
        auth_headers["etag"] = "*"  # for now, send in the wildcard to skip around etag checking

        # disable
        payload = {"isEnabled": False}
        response = await client.patch(full_endpoint, headers=auth_headers, json=payload, timeout=TIMEOUT)
        LOGGER.info(f'RESPONSE Status code: {response.status_code} Content: {response.content}')
        assert (response.status_code == status.HTTP_202_ACCEPTED), "Disable resource failed"
        operation_endpoint = response.headers["Location"]
        await wait_for(patch_done, client, operation_endpoint, auth_headers, [strings.RESOURCE_STATUS_UPDATING_FAILED])

        # delete
        response = await client.delete(full_endpoint, headers=auth_headers, timeout=TIMEOUT)
        LOGGER.info(f'RESPONSE Status code: {response.status_code} Content: {response.content}')
        assert (response.status_code == status.HTTP_200_OK), "The resource couldn't be deleted"

        resource_id = response.json()["operation"]["resourceId"]
        operation_endpoint = response.headers["Location"]

        await wait_for(delete_done, client, operation_endpoint, auth_headers, [strings.RESOURCE_STATUS_DELETING_FAILED])
        return resource_id


async def wait_for(func, client, operation_endpoint, headers, failure_states: list):
    done, done_state, message = await func(client, operation_endpoint, headers)
    while not done:
        LOGGER.info(f'WAITING FOR OP: {operation_endpoint}')
        await asyncio.sleep(30)

        done, done_state, message = await func(client, operation_endpoint, headers)
        LOGGER.info(f"{done}, {done_state}, {message}")
    try:
        assert done_state not in failure_states
    except Exception:
        LOGGER.exception(f"Failed to deploy status message: {message}")
        raise
