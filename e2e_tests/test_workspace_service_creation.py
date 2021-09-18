import pytest
import asyncio

from contextlib import asynccontextmanager
from httpx import AsyncClient
from starlette import status

from test_workspace_creation import disable_and_delete_workspace, post_workspace_template

import config
from resources import strings


pytestmark = pytest.mark.asyncio


class InstallFailedException(Exception):
    pass


workspace_service_templates = [
    (strings.AZUREML_SERVICE),
    (strings.DEVTESTLABS_SERVICE),
    (strings.GUACAMOLE_SERVICE),
    (strings.INNEREYE_DEEPLEARNING_SERVICE),
    (strings.INNEREYE_INFERENCE_SERVICE)
]


@asynccontextmanager
async def get_service_template(template_name, token, verify):
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.get(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_SERVICE_TEMPLATES}/{template_name}",
            headers=headers)
        yield response


async def install_service_done(client, workspace_id, workspace_service_id, headers):
    install_terminal_states = [strings.RESOURCE_STATUS_DEPLOYED, strings.RESOURCE_STATUS_FAILED]
    status, message = await check_service_deployment(client, workspace_id, workspace_service_id, headers)
    return (True, status, message) if status in install_terminal_states else (False, status, message)


async def delete_service_done(client, workspace_id, workspace_service_id, headers):
    delete_terminal_states = [strings.RESOURCE_STATUS_DELETED, strings.RESOURCE_STATUS_DELETING_FAILED]
    status, message = await check_service_deployment(client, workspace_id, workspace_service_id, headers)
    return (True, status, message) if status in delete_terminal_states else (False, status, message)


async def check_service_deployment(client, workspace_id, workspace_service_id, headers) -> bool:
    response = await client.get(
        f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspace_id}/{strings.API_WORKSPACE_SERVICES}/{workspace_service_id}",
        headers=headers)
    if response.status_code == 200:
        status = response.json()["workspaceService"]["deployment"]["status"]
        message = response.json()["workspaceService"]["deployment"]["message"]
        return (status, message)
    elif response.status_code == 404:
        # Seems like the resource got deleted
        return (strings.RESOURCE_STATUS_DELETED, "Workspace service was deleted")


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
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.post(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspace_id}/{strings.API_WORKSPACE_SERVICES}",
            headers=headers, json=payload)

        assert (response.status_code == status.HTTP_202_ACCEPTED), f"Request for workspace service {payload['workspaceServiceType']} creation failed"

        workspace_service_id = response.json()["workspaceServiceId"]

        try:
            await wait_for_service(install_service_done, client, workspace_id, workspace_service_id, headers, strings.RESOURCE_STATUS_FAILED)
            return workspace_service_id, True
        except Exception:
            return workspace_service_id, False


async def disable_workspace_service(workspace_id, workspace_service_id, token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        payload = {"enabled": "false"}

        response = await client.patch(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspace_id}/{strings.API_WORKSPACE_SERVICES}/{workspace_service_id}",
            headers=headers, json=payload)

        enabled = response.json()["workspaceService"]["resourceTemplateParameters"]["enabled"]
        assert (enabled is False), "The workspace service wasn't disabled"


async def delete_workspace_service(workspace_id, workspace_service_id, token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.delete(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspace_id}/{strings.API_WORKSPACE_SERVICES}/{workspace_service_id}",
            headers=headers)

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


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_service_templates)
async def test_get_workspace_service_templates(template_name, token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.get(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_SERVICE_TEMPLATES}",
            headers=headers)

        template_names = [templates["name"] for templates in response.json()["templates"]]
        assert (template_name in template_names), f"No {template_name} template found"


@pytest.mark.smoke
@pytest.mark.parametrize("template_name", workspace_service_templates)
async def test_getting_templates(template_name, token, verify) -> None:
    async with get_service_template(template_name, token, verify) as response:
        assert (response.status_code == status.HTTP_200_OK), f"GET Request for {template_name} creation failed"


@pytest.mark.smoke
@pytest.mark.timeout(3000)
async def test_create_guacamole_service_into_base_workspace(token, verify) -> None:
    payload = {
        "workspaceType": "tre-workspace-base",
        "properties": {
            "display_name": "E2E test guacamole service",
            "description": "workspace for E2E",
            "app_id": f"{config.AUTH_APP_CLIENT_ID}"
        }
    }
    workspace_id, install_status = await post_workspace_template(payload, token, verify)

    # Enable when guacamole deletion bug is fixed
    #############################################
    # service_payload = {
    #    "workspaceServiceType": "tre-service-guacamole",
    #    "properties": {
    #        "display_name": "Workspace service test",
    #        "description": "Workspace service for E2E test"
    #    }
    #}

    # workspace_service_id, install_service_status = await post_workspace_service_template(workspace_id, service_payload, token, verify)

    # await disable_and_delete_workspace_service(workspace_id, workspace_service_id, install_service_status, token, verify)

    await disable_and_delete_workspace(workspace_id, install_status, token, verify)
