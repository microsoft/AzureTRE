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
async def get_template(template_name, token, verify):
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_TEMPLATES}/{template_name}", headers=headers)
        yield response


async def install_done(client, workspace_id, headers) -> (bool, str, str):
    install_terminal_states = [strings.RESOURCE_STATUS_DEPLOYED, strings.RESOURCE_STATUS_FAILED]
    deployment_status, message = await check_deployment(client, workspace_id, headers)
    return (True, deployment_status, message) if deployment_status in install_terminal_states else (False, deployment_status, message)


async def check_deployment(client, workspace_id, headers) -> (str, str):
    response = await client.get(
        f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspace_id}",
        headers=headers)
    if response.status_code == 200:
        deployment_status = response.json()["workspace"]["deployment"]["status"]
        message = response.json()["workspace"]["deployment"]["message"]
        return deployment_status, message
    elif response.status_code == 404:
        # Seems like the resource got deleted
        return strings.RESOURCE_STATUS_DELETED, "Workspace was deleted"


async def post_workspace_template(payload, token, verify) -> (str, bool):
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.post(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}", headers=headers, json=payload)

        assert (response.status_code == status.HTTP_202_ACCEPTED), f"Request for workspace {payload['templateName']} creation failed"

        workspace_id = response.json()["workspaceId"]
        write_workspace_id(workspace_id)

        try:
            await wait_for(install_done, client, workspace_id, headers, strings.RESOURCE_STATUS_FAILED)
            return workspace_id, True
        except Exception:
            return workspace_id, False


async def delete_done(client, workspace_id, headers):
    delete_terminal_states = [strings.RESOURCE_STATUS_DELETED, strings.RESOURCE_STATUS_DELETING_FAILED]
    deployment_status, message = await check_deployment(client, workspace_id, headers)
    return (True, deployment_status, message) if deployment_status in delete_terminal_states else (False, deployment_status, message)


async def wait_for(func, client, workspace_id, headers, failure_state):
    done, done_state, message = await func(client, workspace_id, headers)
    while not done:
        await asyncio.sleep(60)
        done, done_state, message = await func(client, workspace_id, headers)
    try:
        assert done_state != failure_state
    except Exception as e:
        print(f"Failed to deploy status message: {message}")
        print(e)
        raise


async def disable_workspace(token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        payload = {"enabled": "false"}
        workspace_id = read_workspace_id()

        response = await client.patch(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspace_id}", headers=get_auth_header(token), json=payload)

        enabled = response.json()["workspace"]["resourceTemplateParameters"]["enabled"]
        assert (enabled is False), "The workspace wasn't disabled"


async def disable_and_delete_workspace(workspace_id, install_status, token, verify):
    async with AsyncClient(verify=verify) as client:
        headers = get_auth_header(token)

        await disable_workspace(token, verify)
        await delete_workspace(token, verify)

        try:
            await wait_for(delete_done, client, workspace_id, headers, strings.RESOURCE_STATUS_DELETING_FAILED)
        except Exception:
            raise
        finally:
            if not install_status:
                raise InstallFailedException("Install was not done successfully")


async def delete_workspace(token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        workspace_id = read_workspace_id()

        response = await client.delete(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspace_id}", headers=get_auth_header(token))

        assert (response.status_code == status.HTTP_200_OK), "The workspace couldn't be deleted"


@asynccontextmanager
async def get_service_template(template_name, token, verify):
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_SERVICE_TEMPLATES}/{template_name}", headers=headers)
        yield response


async def install_service_done(client, workspace_id, workspace_service_id, headers):
    install_terminal_states = [strings.RESOURCE_STATUS_DEPLOYED, strings.RESOURCE_STATUS_FAILED]
    deployment_status, message = await check_service_deployment(client, workspace_id, workspace_service_id, headers)
    return (True, deployment_status, message) if deployment_status in install_terminal_states else (False, deployment_status, message)


async def delete_service_done(client, workspace_id, workspace_service_id, headers):
    delete_terminal_states = [strings.RESOURCE_STATUS_DELETED, strings.RESOURCE_STATUS_DELETING_FAILED]
    deployment_status, message = await check_service_deployment(client, workspace_id, workspace_service_id, headers)
    return (True, deployment_status, message) if deployment_status in delete_terminal_states else (False, deployment_status, message)


async def check_service_deployment(client, workspace_id, workspace_service_id, headers) -> (str, str):
    response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspace_id}/{strings.API_WORKSPACE_SERVICES}/{workspace_service_id}", headers=headers)
    if response.status_code == 200:
        deployment_status = response.json()["workspaceService"]["deployment"]["status"]
        message = response.json()["workspaceService"]["deployment"]["message"]
        return deployment_status, message
    elif response.status_code == 404:
        # Seems like the resource got deleted
        return strings.RESOURCE_STATUS_DELETED, "Workspace service was deleted"


async def wait_for_service(func, client, workspace_id, workspace_service_id, headers, failure_state):
    done, done_state, message = await func(client, workspace_id, workspace_service_id, headers)
    while not done:
        await asyncio.sleep(60)
        done, done_state, message = await func(client, workspace_id, workspace_service_id, headers)
    try:
        assert done_state != failure_state
    except Exception as e:
        print(f"Failed to deploy status message: {message}")
        print(e)
        raise


async def post_workspace_service_template(workspace_id, payload, token, verify):
    async with AsyncClient(verify=verify) as client:
        response = await client.post(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspace_id}/{strings.API_WORKSPACE_SERVICES}", headers=get_auth_header(token), json=payload)

        assert (response.status_code == status.HTTP_202_ACCEPTED), f"Request for workspace service {payload['templateName']} creation failed"

        workspace_service_id = response.json()["workspaceServiceId"]

        try:
            await wait_for_service(install_service_done, client, workspace_id, workspace_service_id, get_auth_header(token), strings.RESOURCE_STATUS_FAILED)
            return workspace_service_id, True
        except Exception:
            return workspace_service_id, False


async def disable_workspace_service(workspace_id, workspace_service_id, token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        payload = {"enabled": "false"}

        response = await client.patch(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspace_id}/{strings.API_WORKSPACE_SERVICES}/{workspace_service_id}", headers=get_auth_header(token), json=payload)

        enabled = response.json()["workspaceService"]["resourceTemplateParameters"]["enabled"]
        assert (enabled is False), "The workspace service wasn't disabled"


async def delete_workspace_service(workspace_id, workspace_service_id, token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        response = await client.delete(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspace_id}/{strings.API_WORKSPACE_SERVICES}/{workspace_service_id}", headers=get_auth_header(token))
        assert (response.status_code == status.HTTP_200_OK), "The workspace service couldn't be deleted"


async def disable_and_delete_workspace_service(workspace_id, workspace_service_id, install_status, token, verify):
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        await disable_workspace_service(workspace_id, workspace_service_id, token, verify)
        await delete_workspace_service(workspace_id, workspace_service_id, token, verify)

        try:
            await wait_for_service(delete_service_done, client, workspace_id, workspace_service_id, headers, strings.RESOURCE_STATUS_DELETING_FAILED)
        except Exception:
            raise
        finally:
            if not install_status:
                raise InstallFailedException("Install was not done successfully")
