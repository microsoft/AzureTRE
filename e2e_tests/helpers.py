import asyncio
from typing import Optional
from contextlib import asynccontextmanager
from httpx import AsyncClient, Timeout
import logging
from starlette import status


import config
from resources import strings


LOGGER = logging.getLogger(__name__)
TIMEOUT = Timeout(10, read=30)


class InstallFailedException(Exception):
    pass


def read_workspace_id() -> str:
    with open('workspace_id.txt', 'r') as f:
        workspace_id = f.readline()
    return workspace_id


def write_workspace_id(workspace_id: str) -> None:
    with open('workspace_id.txt', 'w') as f:
        f.write(workspace_id)


def get_auth_header(token: str) -> dict:
    return {'Authorization': f'Bearer {token}'}


@asynccontextmanager
async def get_template(template_name, endpoint, admin_token, verify):
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {admin_token}'}

        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{endpoint}/{template_name}", headers=headers, timeout=TIMEOUT)
        yield response


async def post_resource(payload, endpoint, resource_type, token, admin_token, verify, method="POST", wait=True):
    async with AsyncClient(verify=verify, timeout=30.0) as client:

        if resource_type == 'workspace':
            auth_headers = get_auth_header(admin_token)
        else:
            auth_headers = get_auth_header(token)

        if (config.TRE_URL != ""):
            full_endpoint = f"{config.TRE_URL}{endpoint}"
        else:
            full_endpoint = f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{endpoint}"
        LOGGER.info(f'POSTING RESOURCE TO: {full_endpoint}')

        if method == "POST":
            response = await client.post(full_endpoint, headers=auth_headers, json=payload, timeout=TIMEOUT)
            check_method = install_done
        else:
            auth_headers["eTag"] = "*"  # * = force the update regardless. We have other tests to check the validity of the etag
            check_method = patch_done
            response = await client.patch(full_endpoint, headers=auth_headers, json=payload, timeout=TIMEOUT)

        LOGGER.info(f'RESPONSE Status code: {response.status_code} Content: {response.content}')
        assert (response.status_code == status.HTTP_202_ACCEPTED), f"Request for resource {payload['templateName']} creation failed"

        resource_path = response.json()["operation"]["resourcePath"]
        resource_id = response.json()["operation"]["resourceId"]
        operation_endpoint = response.headers["Location"]

        if wait:
            await wait_for(check_method, client, operation_endpoint, get_auth_header(token), strings.RESOURCE_STATUS_FAILED)

        return resource_path, resource_id


async def get_shared_service_id_by_name(template_name: str, verify, token) -> Optional[dict]:
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        endpoint = '/api/shared-services'
        full_endpoint = f'https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{endpoint}'
        LOGGER.info(f'URL: {full_endpoint}')

        auth_headers = get_auth_header(token)

        response = await client.get(full_endpoint, headers=auth_headers, timeout=TIMEOUT)
        LOGGER.info(f'RESPONSE: {response} {response.json()}')
        assert (response.status_code == status.HTTP_200_OK), "Request to get shared services failed"

        shared_service_list = response.json()["sharedServices"]
        matching_shared_services = [service for service in shared_service_list if service["templateName"] == template_name and service["isActive"]]
        if len(matching_shared_services) == 0:
            return None
        assert len(matching_shared_services) == 1, f"There can be at most one active shared service with template name {template_name}"
        return matching_shared_services[0]


async def disable_and_delete_resource(endpoint, resource_type, token, admin_token, verify):
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:

        if resource_type == 'workspace':
            auth_headers = get_auth_header(admin_token)
        else:
            auth_headers = get_auth_header(token)

        auth_headers["etag"] = "*"  # for now, send in the wildcard to skip around etag checking

        full_endpoint = f'https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{endpoint}'

        # disable
        payload = {"isEnabled": False}
        response = await client.patch(full_endpoint, headers=auth_headers, json=payload, timeout=TIMEOUT)
        LOGGER.info(f'RESPONSE Status code: {response.status_code} Content: {response.content}')
        assert (response.status_code == status.HTTP_202_ACCEPTED), "Disable resource failed"
        operation_endpoint = response.headers["Location"]
        await wait_for(patch_done, client, operation_endpoint, auth_headers, strings.RESOURCE_STATUS_FAILED)

        # delete
        response = await client.delete(full_endpoint, headers=auth_headers, timeout=TIMEOUT)
        assert (response.status_code == status.HTTP_200_OK), "The resource couldn't be deleted"

        resource_id = response.json()["operation"]["resourceId"]
        operation_endpoint = response.headers["Location"]

        owner_auth_headers = get_auth_header(token)
        await wait_for(delete_done, client, operation_endpoint, owner_auth_headers, strings.RESOURCE_STATUS_DELETING_FAILED)
        return resource_id


async def ping_guacamole_workspace_service(workspace_id, workspace_service_id, token, verify) -> None:
    short_workspace_id = workspace_id[-4:]
    short_workspace_service_id = workspace_service_id[-4:]
    endpoint = f"https://guacamole-{config.TRE_ID}-ws-{short_workspace_id}-svc-{short_workspace_service_id}.azurewebsites.net/guacamole"
    headers = {'x-access-token': f'{token}'}
    terminal_http_status = [status.HTTP_200_OK,
                            status.HTTP_401_UNAUTHORIZED,
                            status.HTTP_403_FORBIDDEN,
                            status.HTTP_302_FOUND  # usually means auth header wasn't accepted
                            ]

    async with AsyncClient(verify=verify) as client:
        while (True):
            try:
                response = await client.get(url=endpoint, headers=headers, timeout=TIMEOUT)
                LOGGER.info(f"GUAC RESPONSE: {response}")

                if response.status_code in terminal_http_status:
                    break

                await asyncio.sleep(30)

            except Exception:
                LOGGER.exception("Generic execption in ping.")

        assert (response.status_code == status.HTTP_200_OK), "Guacamole cannot be reached"


async def wait_for(func, client, operation_endoint, headers, failure_state):
    done, done_state, message = await func(client, operation_endoint, headers)
    while not done:
        LOGGER.info(f'WAITING FOR OP: {operation_endoint}')
        await asyncio.sleep(30)

        done, done_state, message = await func(client, operation_endoint, headers)
        LOGGER.info(f"{done}, {done_state}, {message}")
    try:
        assert done_state != failure_state
    except Exception:
        LOGGER.exception(f"Failed to deploy status message: {message}")
        raise


async def delete_done(client, operation_endpoint, headers):
    delete_terminal_states = [strings.RESOURCE_STATUS_DELETED, strings.RESOURCE_STATUS_DELETING_FAILED, strings.RESOURCE_ACTION_STATUS_PIPELINE_SUCCEEDED, strings.RESOURCE_ACTION_STATUS_PIPELINE_FAILED]
    deployment_status, message = await check_deployment(client, operation_endpoint, headers)
    return (True, deployment_status, message) if deployment_status in delete_terminal_states else (False, deployment_status, message)


async def install_done(client, operation_endpoint, headers):
    install_terminal_states = [strings.RESOURCE_STATUS_DEPLOYED, strings.RESOURCE_STATUS_FAILED, strings.RESOURCE_ACTION_STATUS_PIPELINE_SUCCEEDED, strings.RESOURCE_ACTION_STATUS_PIPELINE_FAILED]
    deployment_status, message = await check_deployment(client, operation_endpoint, headers)
    return (True, deployment_status, message) if deployment_status in install_terminal_states else (False, deployment_status, message)


async def patch_done(client, operation_endpoint, headers):
    install_terminal_states = [strings.RESOURCE_ACTION_STATUS_SUCCEEDED, strings.RESOURCE_ACTION_STATUS_FAILED, strings.RESOURCE_ACTION_STATUS_PIPELINE_SUCCEEDED, strings.RESOURCE_ACTION_STATUS_PIPELINE_FAILED]
    deployment_status, message = await check_deployment(client, operation_endpoint, headers)
    return (True, deployment_status, message) if deployment_status in install_terminal_states else (False, deployment_status, message)


async def check_deployment(client, operation_endpoint, headers):
    response = await client.get(
        f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{operation_endpoint}", headers=headers, timeout=TIMEOUT)
    if response.status_code == 200:
        deployment_status = response.json()["operation"]["status"]
        message = response.json()["operation"]["message"]
        return deployment_status, message
    else:
        LOGGER.error(f"Non 200 response in check_deployment: {response.status_code}")
        LOGGER.error(f"Full response: {response}")
        raise Exception("Non 200 response in check_deployment")
