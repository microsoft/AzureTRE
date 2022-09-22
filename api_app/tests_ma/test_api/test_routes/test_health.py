import pytest
from httpx import AsyncClient
from mock import patch

from models.schemas.status import StatusEnum
from resources import strings

pytestmark = pytest.mark.asyncio


@patch("api.routes.health.create_resource_processor_status")
@patch("api.routes.health.create_service_bus_status")
@patch("api.routes.health.create_state_store_status")
async def test_health_response_contains_cosmos_status(health_check_cosmos_mock, health_check_service_bus_mock, health_check_rp_mock, app,
                                                      client: AsyncClient) -> None:
    message = ""
    health_check_cosmos_mock.return_value = StatusEnum.ok, message
    health_check_service_bus_mock.return_value = StatusEnum.ok, message
    health_check_rp_mock.return_value = StatusEnum.ok, message
    response = await client.get(app.url_path_for(strings.API_GET_HEALTH_STATUS))

    assert {"message": message, "service": strings.COSMOS_DB, "status": strings.OK} in response.json()["services"]


@patch("api.routes.health.create_resource_processor_status")
@patch("api.routes.health.create_service_bus_status")
@patch("api.routes.health.create_state_store_status")
async def test_health_response_contains_service_bus_status(health_check_cosmos_mock, health_check_service_bus_mock, health_check_rp_mock, app,
                                                           client: AsyncClient) -> None:
    message = ""
    health_check_cosmos_mock.return_value = StatusEnum.ok, message
    health_check_service_bus_mock.return_value = StatusEnum.ok, message
    health_check_rp_mock.return_value = StatusEnum.ok, message
    response = await client.get(app.url_path_for(strings.API_GET_HEALTH_STATUS))

    assert {"message": message, "service": strings.SERVICE_BUS, "status": strings.OK} in response.json()["services"]


@patch("api.routes.health.create_resource_processor_status")
@patch("api.routes.health.create_service_bus_status")
@patch("api.routes.health.create_state_store_status")
async def test_health_response_contains_resource_processor_status(health_check_cosmos_mock, health_check_service_bus_mock, health_check_rp_mock, app,
                                                                  client: AsyncClient) -> None:
    message = ""
    health_check_cosmos_mock.return_value = StatusEnum.ok, message
    health_check_service_bus_mock.return_value = StatusEnum.ok, message
    health_check_rp_mock.return_value = StatusEnum.ok, message
    response = await client.get(app.url_path_for(strings.API_GET_HEALTH_STATUS))

    assert {"message": message, "service": strings.RESOURCE_PROCESSOR, "status": strings.OK} in response.json()["services"]
