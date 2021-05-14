import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from api.resources import strings


pytestmark = pytest.mark.asyncio


async def test_ping(app: FastAPI, client: AsyncClient) -> None:
    response = await client.get(app.url_path_for("ping:get-server-alive"))
    assert response.json()["message"] == strings.PONG
