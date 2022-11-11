import pytest
from httpx import AsyncClient

import config
from resources import strings


pytestmark = pytest.mark.asyncio


@pytest.mark.smoke
async def test_api_health() -> None:
    async with AsyncClient(verify=False) as client:
        url = f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_HEALTH}"
        response = await client.get(url)
        assert response.status_code == 200
        assert response.json()["services"] == [
            {"service": "Cosmos DB", "status": "OK", "message": ""},
            {"service": "Service Bus", "status": "OK", "message": ""},
            {"service": "Resource Processor", "status": "OK", "message": ""},
        ]
