import pytest
from httpx import AsyncClient
from resources import strings
from starlette import status
import config
import time

pytestmark = pytest.mark.asyncio


async def authenticate() -> str:
    async with AsyncClient() as client:

        headers = {'content-type': "application/x-www-form-urlencoded"}
        payload = f"grant_type=password&resource={config.RESOURCE}&username={config.USERNAME}&password={config.PASSWORD}&scope={config.SCOPE}&client_id={config.CLIENT_ID}"

        response = await client.post(f"https://login.microsoftonline.com/{config.AUTH_TENANT_ID}/oauth2/token", headers=headers, data=payload)
        if (response.status_code == status.HTTP_200_OK):
            return response.json()["access_token"]
        else:
            return None


async def test_get_workspace_templates() -> None:
    token = await authenticate()

    assert token is not None, "Token not returned"

    async with AsyncClient() as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_TEMPLATES}", headers=headers)

        assert (strings.VANILLA_WORKSPACE in response.json()["templateNames"]), "No vanilla workspace found"


async def test_get_vanilla_workspace_template() -> None:
    token = await authenticate()

    assert token is not None, "Token not returned"

    async with AsyncClient() as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_TEMPLATES}/{strings.VANILLA_WORKSPACE}", headers=headers)

        assert (response.status_code == status.HTTP_200_OK), "Request for workspace creation failed"


async def deployment_started(client, workspaceId, headers) -> bool:
    response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspaceId}", headers=headers)

    if response.json()["workspace"]["deployment"]["status"] == strings.NOT_DEPLOYED:
        return False
    else:
        return True


async def test_create_vanilla_workspace() -> None:
    token = await authenticate()

    assert token is not None, "Token not returned"

    async with AsyncClient() as client:
        headers = {'Authorization': f'Bearer {token}'}

        payload = {"displayName": "My workspace",
                   "description": "workspace for team X",
                   "workspaceType": "tre-workspace-vanilla",
                   "parameters": "",
                   "authConfig":
                    {"provider":"AAD",
                     "data":
                     {
                         "app_id": f"{config.AUTH_APP_CLIENT_ID}"
                     }
                    }
                   }

        response = await client.post(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}", headers=headers, json=payload)

        assert (response.status_code == status.HTTP_202_ACCEPTED), "Request for workspace creation failed"

        workspaceId = response.json()["workspaceId"]

        while not await deployment_started(client, workspaceId, headers):
            time.sleep(10)
