import pytest
from mock import patch
from fastapi import FastAPI
from httpx import AsyncClient
from api.resources import strings
from api.models.schemas.health import StatusEnum


pytestmark = pytest.mark.asyncio


@patch("api.routes.health.get_state_store_status")
async def test_health_response_contains_cosmos_status(health_check_mock, app: FastAPI, client: AsyncClient) -> None:
    message = ""
    health_check_mock.return_value = StatusEnum.ok, message

    response = await client.get(app.url_path_for("health:get-status-of-services"))

    assert {"message": message, "service": strings.COSMOS_DB, "status": strings.OK} in response.json()["services"]
