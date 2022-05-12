from json import JSONDecodeError
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
        responseJson = ""
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        if config.TEST_ACCOUNT_CLIENT_ID != "" and config.TEST_ACCOUNT_CLIENT_SECRET != "":
            # Use Client Credentials flow
            payload = f"grant_type=client_credentials&client_id={config.TEST_ACCOUNT_CLIENT_ID}&client_secret={config.TEST_ACCOUNT_CLIENT_SECRET}&scope=api://{config.API_CLIENT_ID}/.default"
            url = f"https://login.microsoftonline.com/{config.AAD_TENANT_ID}/oauth2/v2.0/token"

        else:
            # Use Resource Owner Password Credentials flow
            payload = f"grant_type=password&resource={config.API_CLIENT_ID}&username={config.TEST_USER_NAME}&password={config.TEST_USER_PASSWORD}&scope=api://{config.API_CLIENT_ID}/user_impersonation&client_id={config.TEST_APP_ID}"
            url = f"https://login.microsoftonline.com/{config.AAD_TENANT_ID}/oauth2/token"

        response = await client.post(url, headers=headers, content=payload)
        try:
            responseJson = response.json()
        except JSONDecodeError:
            assert False, "Failed to parse response as JSON: {}".format(response.content)

        assert "access_token" in responseJson, "Failed to get access_token: {}".format(response.content)
        token = responseJson["access_token"]
        assert token is not None, "Token not returned"
        return token if (response.status_code == status.HTTP_200_OK) else None
