import pytest
from httpx import AsyncClient

import config


pytestmark = pytest.mark.asyncio


@pytest.mark.smoke
async def test_ui() -> None:
    endpoint = f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com"

    async with AsyncClient(verify=False) as client:
        response = await client.get(endpoint)
        assert response.status_code == 200
        assert "<title>Azure TRE</title>" in response.text
