import pytest
from httpx import AsyncClient
from resources import strings
import config

pytestmark = pytest.mark.asyncio


async def test_health() -> None:
    async with AsyncClient() as client:
        response = await client.get(f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{strings.API_HEALTH}")
        assert response.json()["message"] == strings.PONG
