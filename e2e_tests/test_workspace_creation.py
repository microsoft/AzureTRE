import pytest
import asyncio

from contextlib import asynccontextmanager
from httpx import AsyncClient
from starlette import status

import config
from shared import token, verify
from resources import strings


pytestmark = pytest.mark.asyncio


workspace_templates = [
    (strings.VANILLA_WORKSPACE),
    (strings.DEV_TEST_LABS),
    (strings.INNEREYE_DEEPLEARNING),
    (strings.INNEREYE_DEEPLEARNING_INFERENCE)
]


@asynccontextmanager
async def get_template(template_name, token, verify):
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.get(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_TEMPLATES}/{template_name}",
            headers=headers)
        yield response


async def deployment_done(client, workspaceid, headers) -> bool:
    response = await client.get(
        f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspaceid}",
        headers=headers)
    status = response.json()["workspace"]["deployment"]["status"]
    message = response.json()["workspace"]["deployment"]["message"]
    return (True, status, message) if status in [strings.RESOURCE_STATUS_DEPLOYED, strings.RESOURCE_STATUS_FAILED] else (False, status, message)


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

        done, done_state, message = await deployment_done(client, workspaceid, headers)
        while not done:
            await asyncio.sleep(60)
            done, done_state, message = await deployment_done(client, workspaceid, headers)
        try:
            assert done_state != strings.RESOURCE_STATUS_FAILED
        except AssertionError as e:
            print(f"Failed deployment status message: {message}")
            print(e)
            raise AssertionError


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


@pytest.mark.smoke
@pytest.mark.timeout(1200)
async def test_create_vanilla_workspace(token, verify) -> None:
    payload = {
        "workspaceType": "tre-workspace-vanilla",
        "properties": {
            "display_name": "E2E test",
            "description": "workspace for E2E",
            "app_id": f"{config.AUTH_APP_CLIENT_ID}",
            "address_space": "192.168.25.0/24"  # Reserving this for E2E tests.
        }
    }
    await post_workspace_template(payload, token, verify)


@pytest.mark.smoke
async def test_disable_vanilla_workspace(token, verify) -> None:
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


@pytest.mark.smoke
async def test_delete_vanilla_workspace(token, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {token}'}

        with open('workspace_id.txt', 'r') as f:
            workspaceid = f.readline()

        response = await client.delete(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspaceid}",
            headers=headers)

        assert (response.status_code == status.HTTP_200_OK), "The workspace couldn't be deleted"


@pytest.mark.extended
@pytest.mark.timeout(1800)
async def test_create_devtestlabs_workspace(token, verify) -> None:
    payload = {
        "workspaceType": "tre-workspace-azureml-devtestlabs",
        "properties": {
            "display_name": "E2E test",
            "description": "workspace for E2E",
            "app_id": f"{config.AUTH_APP_CLIENT_ID}",
            "address_space": "192.168.25.0/24",
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
            "address_space": "192.168.25.0/24",
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
            "address_space": "192.168.25.0/24",
            "acr_name": f"{config.ACR_NAME}"
        }
    }
    await post_workspace_template(payload, token, verify)
