import asyncio

from contextlib import asynccontextmanager
from httpx import AsyncClient
from starlette import status

import config
from resources import strings


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
async def get_template(template_name, admin_token, verify):
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {admin_token}'}

        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_TEMPLATES}/{template_name}", headers=headers)
        yield response


@asynccontextmanager
async def get_service_template(template_name, token, verify):
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_SERVICE_TEMPLATES}/{template_name}", headers=headers)
        yield response


async def post_resource(payload, endpoint, resource_type, token, admin_token, verify):
    async with AsyncClient(verify=verify) as client:

        if resource_type == 'workspace':
            auth_headers = get_auth_header(admin_token)
        else:
            auth_headers = get_auth_header(token)

        full_endpoint = f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{endpoint}"
        print(f'POSTING RESOURCE TO: {full_endpoint}')

        response = await client.post(full_endpoint, headers=auth_headers, json=payload)

        assert (response.status_code == status.HTTP_202_ACCEPTED), f"Request for resource {payload['templateName']} creation failed"

        resource_path = response.json()["operation"]["resourcePath"]
        resource_id = response.json()["operation"]["resourceId"]
        operation_endpoint = response.headers["Location"]

        await wait_for(install_done, client, operation_endpoint, get_auth_header(token), strings.RESOURCE_STATUS_FAILED)
        return resource_path, resource_id


async def disable_and_delete_resource(endpoint, resource_type, token, admin_token, verify):
    async with AsyncClient(verify=verify) as client:

        if resource_type == 'workspace':
            auth_headers = get_auth_header(admin_token)
        else:
            auth_headers = get_auth_header(token)

        auth_headers["etag"] = "*"  # for now, send in the wildcard to skip around etag checking

        full_endpoint = f'https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{endpoint}'

        # disable
        payload = {"isEnabled": False}
        response = await client.patch(full_endpoint, headers=auth_headers, json=payload)
        assert (response.status_code == status.HTTP_200_OK), "Disable resource failed"

        # delete
        response = await client.delete(full_endpoint, headers=auth_headers)
        assert (response.status_code == status.HTTP_200_OK), "The resource couldn't be deleted"

        resource_id = response.json()["operation"]["resourceId"]
        operation_endpoint = response.headers["Location"]

        owner_auth_headers = get_auth_header(token)
        await wait_for(delete_done, client, operation_endpoint, owner_auth_headers, strings.RESOURCE_STATUS_DELETING_FAILED)
        return resource_id


async def ping_guacamole_workspace_service(workspace_id, workspace_service_id, token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        short_workspace_id = workspace_id[-4:]
        short_workspace_service_id = workspace_service_id[-4:]
        response = await client.get(f"https://guacamole-{config.TRE_ID}-ws-{short_workspace_id}-svc-{short_workspace_service_id}.azurewebsites.net/guacamole", headers={'x-access-token': f'{token}'}, timeout=300)
        print("GUAC RESPONSE", response)
        assert (response.status_code == status.HTTP_200_OK), "Guacamole cannot be reached"


async def wait_for(func, client, operation_endoint, headers, failure_state):
    done, done_state, message = await func(client, operation_endoint, headers)
    while not done:
        print(f'WAITING FOR OP: {operation_endoint}')
        await asyncio.sleep(30)

        done, done_state, message = await func(client, operation_endoint, headers)
        print(done, done_state, message)
    try:
        assert done_state != failure_state
    except Exception as e:
        print(f"Failed to deploy status message: {message}")
        print(e)
        raise


async def delete_done(client, operation_endpoint, headers):
    delete_terminal_states = [strings.RESOURCE_STATUS_DELETED, strings.RESOURCE_STATUS_DELETING_FAILED]
    deployment_status, message = await check_deployment(client, operation_endpoint, headers)
    return (True, deployment_status, message) if deployment_status in delete_terminal_states else (False, deployment_status, message)


async def install_done(client, operation_endpoint, headers):
    install_terminal_states = [strings.RESOURCE_STATUS_DEPLOYED, strings.RESOURCE_STATUS_FAILED]
    deployment_status, message = await check_deployment(client, operation_endpoint, headers)
    return (True, deployment_status, message) if deployment_status in install_terminal_states else (False, deployment_status, message)


async def check_deployment(client, operation_endpoint, headers):
    response = await client.get(
        f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{operation_endpoint}", headers=headers)
    if response.status_code == 200:
        deployment_status = response.json()["operation"]["status"]
        message = response.json()["operation"]["message"]
        return deployment_status, message
    else:
        raise Exception("Non 200 response in check_deployment")
