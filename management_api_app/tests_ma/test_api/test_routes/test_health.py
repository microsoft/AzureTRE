import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from resources import strings


pytestmark = pytest.mark.asyncio


async def test_health(app: FastAPI, client: AsyncClient) -> None:
    response = await client.get(app.url_path_for(strings.API_GET_HEALTH_STATUS))
    assert response.json()["message"] == strings.PONG
