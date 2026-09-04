import pytest
from httpx import AsyncClient
from mock import patch, MagicMock

from models.schemas.status import StatusEnum
from resources import strings
from service_bus.service_bus_consumer import ServiceBusConsumer

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


@patch("api.routes.health.create_resource_processor_status")
@patch("api.routes.health.create_service_bus_status")
@patch("api.routes.health.create_state_store_status")
async def test_health_response_contains_consumer_statuses(health_check_cosmos_mock, health_check_service_bus_mock, health_check_rp_mock, app,
                                                          client: AsyncClient) -> None:
    """Test that health endpoint includes deployment and airlock consumer status."""
    message = ""
    health_check_cosmos_mock.return_value = StatusEnum.ok, message
    health_check_service_bus_mock.return_value = StatusEnum.ok, message
    health_check_rp_mock.return_value = StatusEnum.ok, message

    # Simulate consumers stored on app.state with healthy heartbeats
    mock_deployment_consumer = MagicMock(spec=ServiceBusConsumer)
    mock_deployment_consumer.check_heartbeat.return_value = True
    mock_airlock_consumer = MagicMock(spec=ServiceBusConsumer)
    mock_airlock_consumer.check_heartbeat.return_value = True
    app.state.deployment_status_updater = mock_deployment_consumer
    app.state.airlock_status_updater = mock_airlock_consumer

    response = await client.get(app.url_path_for(strings.API_GET_HEALTH_STATUS))
    services = response.json()["services"]

    assert {"message": "", "service": strings.DEPLOYMENT_STATUS_CONSUMER, "status": strings.OK} in services
    assert {"message": "", "service": strings.AIRLOCK_STATUS_CONSUMER, "status": strings.OK} in services


@patch("api.routes.health.create_resource_processor_status")
@patch("api.routes.health.create_service_bus_status")
@patch("api.routes.health.create_state_store_status")
async def test_health_response_reports_stale_consumer(health_check_cosmos_mock, health_check_service_bus_mock, health_check_rp_mock, app,
                                                      client: AsyncClient) -> None:
    """Test that health endpoint reports not_ok when a consumer heartbeat is stale."""
    message = ""
    health_check_cosmos_mock.return_value = StatusEnum.ok, message
    health_check_service_bus_mock.return_value = StatusEnum.ok, message
    health_check_rp_mock.return_value = StatusEnum.ok, message

    # Simulate deployment consumer with stale heartbeat
    mock_deployment_consumer = MagicMock(spec=ServiceBusConsumer)
    mock_deployment_consumer.check_heartbeat.return_value = False
    mock_airlock_consumer = MagicMock(spec=ServiceBusConsumer)
    mock_airlock_consumer.check_heartbeat.return_value = True
    app.state.deployment_status_updater = mock_deployment_consumer
    app.state.airlock_status_updater = mock_airlock_consumer

    response = await client.get(app.url_path_for(strings.API_GET_HEALTH_STATUS))
    services = response.json()["services"]

    deploy_svc = next(s for s in services if s["service"] == strings.DEPLOYMENT_STATUS_CONSUMER)
    assert deploy_svc["status"] == strings.NOT_OK
    assert deploy_svc["message"] == strings.CONSUMER_HEARTBEAT_STALE.format(strings.DEPLOYMENT_STATUS_CONSUMER)

    airlock_svc = next(s for s in services if s["service"] == strings.AIRLOCK_STATUS_CONSUMER)
    assert airlock_svc["status"] == strings.OK


@patch("api.routes.health.create_resource_processor_status")
@patch("api.routes.health.create_service_bus_status")
@patch("api.routes.health.create_state_store_status")
async def test_health_response_handles_missing_consumers(health_check_cosmos_mock, health_check_service_bus_mock, health_check_rp_mock, app,
                                                         client: AsyncClient) -> None:
    """Test that health endpoint handles missing consumer references gracefully."""
    message = ""
    health_check_cosmos_mock.return_value = StatusEnum.ok, message
    health_check_service_bus_mock.return_value = StatusEnum.ok, message
    health_check_rp_mock.return_value = StatusEnum.ok, message

    # Remove consumer references from app.state if they exist
    if hasattr(app.state, 'deployment_status_updater'):
        delattr(app.state, 'deployment_status_updater')
    if hasattr(app.state, 'airlock_status_updater'):
        delattr(app.state, 'airlock_status_updater')

    response = await client.get(app.url_path_for(strings.API_GET_HEALTH_STATUS))
    services = response.json()["services"]

    deploy_svc = next(s for s in services if s["service"] == strings.DEPLOYMENT_STATUS_CONSUMER)
    assert deploy_svc["status"] == strings.NOT_OK
    assert deploy_svc["message"] == strings.CONSUMER_NOT_INITIALIZED.format(strings.DEPLOYMENT_STATUS_CONSUMER)
