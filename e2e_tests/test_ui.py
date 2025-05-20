import pytest
from httpx import AsyncClient

import config


pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.smoke
async def test_ui(verify) -> None:
    endpoint = f"{config.TRE_URL}"

    async with AsyncClient(verify) as client:
        response = await client.get(endpoint)
        assert response.status_code == 200
        assert "<title>Azure TRE</title>" in response.text
