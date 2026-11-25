import pytest
from httpx import AsyncClient

import config
from resources import strings


pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.smoke
async def test_health() -> None:
    async with AsyncClient(verify=False) as client:
        url = f"{config.TRE_URL}{strings.API_HEALTH}"
        # Azure management health checks can exceed HTTPX's five-second default.
        response = await client.get(url, timeout=30)
        assert response.status_code == 200
        assert response.json()["services"] == [
            {"service": "Cosmos DB", "status": "OK", "message": ""},
            {"service": "Service Bus", "status": "OK", "message": ""},
            {"service": "Resource Processor", "status": "OK", "message": ""},
        ]
