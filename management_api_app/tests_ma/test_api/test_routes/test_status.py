import pytest
from mock import patch

from fastapi import FastAPI
from httpx import AsyncClient

from models.schemas.status import StatusEnum
from resources import strings


pytestmark = pytest.mark.asyncio


@patch("api.routes.status.create_state_store_status")
async def test_health_response_contains_cosmos_status(health_check_mock, app: FastAPI, client: AsyncClient) -> None:
    message = ""
    health_check_mock.return_value = StatusEnum.ok, message

    response = await client.get(app.url_path_for(strings.API_GET_STATUS_OF_SERVICES))

    assert {"message": message, "service": strings.COSMOS_DB, "status": strings.OK} in response.json()["services"]
