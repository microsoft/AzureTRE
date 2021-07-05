import pytest
from httpx import AsyncClient
from resources import strings
import config

pytestmark = pytest.mark.asyncio


async def test_health() -> None:
    async with AsyncClient(verify=False) as client:
        url = f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_HEALTH}"
        response = await client.get(url)
        assert response.json()["message"] == strings.PONG


async def test_status() -> None:
    async with AsyncClient(verify=False) as client:
        url = f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_STATUS}"
        response = await client.get(url)
        assert response.status_code == 200
        assert response.json()["services"] == [{'service': 'Cosmos DB', 'status': 'OK', 'message': ''}]
