import pytest
from mock import patch
from fastapi import FastAPI
from httpx import AsyncClient
from resources import strings
from models.schemas.health import StatusEnum


pytestmark = pytest.mark.asyncio


@patch("api.routes.status.create_state_store_status")
async def test_health_response_contains_cosmos_status(health_check_mock, app: FastAPI, client: AsyncClient) -> None:
    message = ""
    health_check_mock.return_value = StatusEnum.ok, message

    response = await client.get(app.url_path_for("status:get-status-of-services"))

    assert {"message": message, "service": strings.COSMOS_DB, "status": strings.OK} in response.json()["services"]
