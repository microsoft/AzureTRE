import pytest
import asyncio
import config
from starlette import status
from httpx import AsyncClient
from resources import strings

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def token() -> str:
    async with AsyncClient() as client:

        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        payload = f"grant_type=password&resource={config.RESOURCE}&username={config.USERNAME}&password={config.PASSWORD}&scope={config.SCOPE}&client_id={config.CLIENT_ID}"

        url = f"https://login.microsoftonline.com/{config.AUTH_TENANT_ID}/oauth2/token"
        response = await client.post(url,
                                     headers=headers, data=payload)
        token = response.json()["access_token"]

        assert token is not None, "Token not returned"
        return token if (response.status_code == status.HTTP_200_OK) else None


async def test_get_workspace_templates(token) -> None:

    async with AsyncClient() as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.get(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_TEMPLATES}",
            headers=headers)

        assert (strings.VANILLA_WORKSPACE in response.json()["templateNames"]), "No vanilla workspace found"


async def test_get_vanilla_workspace_template(token) -> None:

    assert token is not None, "Token not returned"

    async with AsyncClient() as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.get(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACE_TEMPLATES}/{strings.VANILLA_WORKSPACE}",
            headers=headers)

        assert (response.status_code == status.HTTP_200_OK), "Request for workspace creation failed"


async def deployment_done(client, workspaceid, headers) -> bool:
    response = await client.get(
        f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}/{workspaceid}",
        headers=headers)
    status = response.json()["workspace"]["deployment"]["status"]
    return (True, status) if status in [strings.RESOURCE_STATUS_DEPLOYED, strings.RESOURCE_STATUS_FAILED] else (False, status)


@pytest.mark.timeout(1200)  # Timeout for vanilla deployment should be 20 mins max
async def test_create_vanilla_workspace(token) -> None:

    assert token is not None, "Token not returned"

    async with AsyncClient() as client:
        headers = {'Authorization': f'Bearer {token}'}

        payload = {"displayName": "E2E test",
                   "description": "workspace for E2E",
                   "workspaceType": "tre-workspace-vanilla",
                   "parameters": {
                       "address_space": "192.168.25.0/24"  # Reserving this for E2E tests.
                   },
                   "authConfig":
                       {"provider": "AAD",
                        "data":
                            {"app_id": f"{config.AUTH_APP_CLIENT_ID}"
                             }
                        }
                   }

        response = await client.post(
            f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_WORKSPACES}",
            headers=headers, json=payload)

        assert (response.status_code == status.HTTP_202_ACCEPTED), "Request for workspace creation failed"

        workspaceid = response.json()["workspaceId"]

        with open('workspace_id.txt', 'w') as f:
            f.write(workspaceid)

        done, done_state = await deployment_done(client, workspaceid, headers)
        while not done:
            await asyncio.sleep(60)
            done, done_state = await deployment_done(client, workspaceid, headers)
        assert done_state != strings.RESOURCE_STATUS_FAILED
