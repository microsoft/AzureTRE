import pytest

from httpx import AsyncClient
from starlette import status

import config

pytestmark = pytest.mark.asyncio


def pytest_addoption(parser):
    parser.addoption("--verify", action="store", default="true")


@pytest.fixture
def verify(pytestconfig):
    if pytestconfig.getoption("verify").lower() == "true":
        return True
    elif pytestconfig.getoption("verify").lower() == "false":
        return False


@pytest.fixture
async def admin_token(verify) -> str:
    async with AsyncClient(verify=verify) as client:

        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        payload = f"grant_type=password&resource={config.RESOURCE}&username={config.USERNAME}&password={config.PASSWORD}&scope={config.SCOPE}&client_id={config.CLIENT_ID}"

        url = f"https://login.microsoftonline.com/{config.AUTH_TENANT_ID}/oauth2/token"
        response = await client.post(url, headers=headers, data=payload)
        token = response.json()["access_token"]

        assert token is not None, "Token not returned"
        return token if (response.status_code == status.HTTP_200_OK) else None


@pytest.fixture
async def workspace_owner_token(verify) -> str:
    async with AsyncClient(verify=verify) as client:

        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        payload = f"grant_type=password&resource={config.AUTH_APP_CLIENT_ID}&username={config.USERNAME}&password={config.PASSWORD}&scope=open_id+profile+email&client_id={config.AUTH_APP_CLIENT_ID}"

        url = f"https://login.microsoftonline.com/{config.AUTH_TENANT_ID}/oauth2/token"
        response = await client.post(url, headers=headers, data=payload)
        token = response.json()["access_token"]

        assert token is not None, "Token not returned"
        return token if (response.status_code == status.HTTP_200_OK) else None
