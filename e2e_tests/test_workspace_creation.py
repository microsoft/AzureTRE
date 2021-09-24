import pytest
import asyncio

from contextlib import asynccontextmanager
from httpx import AsyncClient
from starlette import status

import config
from resources import strings


pytestmark = pytest.mark.asyncio


class InstallFailedException(Exception):
    pass


workspace_templates = [
    (strings.BASE_WORKSPACE),
    (strings.INNEREYE)
]


@asynccontextmanager
async def get_template(template_name, token, verify):
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.get(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_TEMPLATES}/{template_name}",
            headers=headers)
        yield response


async def install_done(client, workspaceid, headers):
    install_terminal_states = [strings.RESOURCE_STATUS_DEPLOYED, strings.RESOURCE_STATUS_FAILED]
    status, message = await check_deployment(client, workspaceid, headers)
    return (True, status, message) if status in install_terminal_states else (False, status, message)


async def delete_done(client, workspaceid, headers):
    delete_terminal_states = [strings.RESOURCE_STATUS_DELETED, strings.RESOURCE_STATUS_DELETING_FAILED]
    status, message = await check_deployment(client, workspaceid, headers)
    return (True, status, message) if status in delete_terminal_states else (False, status, message)


async def check_deployment(client, workspaceid, headers) -> bool:
    response = await client.get(
        f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspaceid}",
        headers=headers)
    if response.status_code == 200:
        status = response.json()["workspace"]["deployment"]["status"]
        message = response.json()["workspace"]["deployment"]["message"]
        return (status, message)
    elif response.status_code == 404:
        # Seems like the resource got delted
        return (strings.RESOURCE_STATUS_DELETED, "Workspace was deleted")


async def wait_for(func, client, workspaceid, headers, failure_state):
    done, done_state, message = await func(client, workspaceid, headers)
    while not done:
        await asyncio.sleep(60)
        done, done_state, message = await func(client, workspaceid, headers)
    try:
        assert done_state != failure_state
    except Exception as e:
        print(f"Failed to deploy status message: {message}")
        print(e)
        raise


async def post_workspace_template(payload, token, verify):
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.post(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}",
            headers=headers, json=payload)

        assert (response.status_code == status.HTTP_202_ACCEPTED), f"Request for workspace {payload['workspaceType']} creation failed"

        workspaceid = response.json()["workspaceId"]

        with open('workspace_id.txt', 'w') as f:
            f.write(workspaceid)

        try:
            await wait_for(install_done, client, workspaceid, headers, strings.RESOURCE_STATUS_FAILED)
            return workspaceid, True
        except Exception:
            return workspaceid, False


async def disable_workspace(token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        with open('workspace_id.txt', 'r') as f:
            workspaceid = f.readline()

        payload = {"enabled": "false"}

        response = await client.patch(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspaceid}",
            headers=headers, json=payload)

        enabled = response.json()["workspace"]["resourceTemplateParameters"]["enabled"]
        assert (enabled is False), "The workspace wasn't disabled"


async def delete_workspace(token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        with open('workspace_id.txt', 'r') as f:
            workspaceid = f.readline()

        response = await client.delete(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspaceid}",
            headers=headers)

        assert (response.status_code == status.HTTP_200_OK), "The workspace couldn't be deleted"


async def disable_and_delete_workspace(workspaceid, install_status, token, verify):
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        await disable_workspace(token, verify)

        await delete_workspace(token, verify)

        try:
            await wait_for(delete_done, client, workspaceid, headers, strings.RESOURCE_STATUS_DELETING_FAILED)
        except Exception:
            raise
        finally:
            if not install_status:
                raise InstallFailedException("Install was not done successfully")


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_templates)
async def test_get_workspace_templates(template_name, token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.get(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_TEMPLATES}",
            headers=headers)

        template_names = [templates["name"] for templates in response.json()["templates"]]
        assert (template_name in template_names), f"No {template_name} template found"


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_templates)
async def test_getting_templates(template_name, token, verify) -> None:
    async with get_template(template_name, token, verify) as response:
        assert (response.status_code == status.HTTP_200_OK), f"GET Request for {template_name} creation failed"


@pytest.mark.extended
@pytest.mark.timeout(1800)
async def test_create_devtestlabs_workspace(token, verify) -> None:
    payload = {
        "workspaceType": "tre-workspace-azureml-devtestlabs",
        "properties": {
            "display_name": "E2E test",
            "description": "workspace for E2E",
            "app_id": f"{config.AUTH_APP_CLIENT_ID}",
            "acr_name": f"{config.ACR_NAME}"
        }
    }
    await post_workspace_template(payload, token, verify)


@pytest.mark.extended
@pytest.mark.timeout(2400)
async def test_create_innereys_dl_workspace(token, verify) -> None:
    payload = {
        "workspaceType": "tre-workspace-azureml-devtestlabs",
        "properties": {
            "display_name": "E2E test",
            "description": "workspace for E2E",
            "app_id": f"{config.AUTH_APP_CLIENT_ID}",
            "acr_name": f"{config.ACR_NAME}"
        }
    }
    await post_workspace_template(payload, token, verify)


@pytest.mark.extended
@pytest.mark.timeout(3000)
async def test_create_innereys_dl_inference_workspace(token, verify) -> None:
    payload = {
        "workspaceType": "tre-workspace-azureml-devtestlabs",
        "properties": {
            "display_name": "E2E test",
            "description": "workspace for E2E",
            "app_id": f"{config.AUTH_APP_CLIENT_ID}",
            "acr_name": f"{config.ACR_NAME}"
        }
    }
    await post_workspace_template(payload, token, verify)
