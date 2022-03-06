from unittest.mock import AsyncMock
from azure.servicebus.exceptions import ServiceBusConnectionError
from mock import patch
from azure.core.exceptions import ServiceRequestError
import pytest

from models.schemas.status import StatusEnum
from resources import strings
from services import health_checker

pytestmark = pytest.mark.asyncio

@patch("services.health_checker.get_store_key")
@patch("services.health_checker.CosmosClient")
def test_get_state_store_status_responding(cosmos_client_mock, get_store_key_mock) -> None:
    get_store_key_mock.return_value = None
    cosmos_client_mock().list_databases.return_value = []
    status, message = health_checker.create_state_store_status()

    assert status == StatusEnum.ok
    assert message == ""


@patch("services.health_checker.get_store_key")
@patch("services.health_checker.CosmosClient")
def test_get_state_store_status_not_responding(cosmos_client_mock, get_store_key_mock) -> None:
    get_store_key_mock.return_value = None
    cosmos_client_mock.return_value = None
    cosmos_client_mock.side_effect = ServiceRequestError(message="some message")

    status, message = health_checker.create_state_store_status()

    assert status == StatusEnum.not_ok
    assert message == strings.STATE_STORE_ENDPOINT_NOT_RESPONDING


@patch("services.health_checker.get_store_key")
@patch("services.health_checker.CosmosClient")
def test_get_state_store_status_other_exception(cosmos_client_mock, get_store_key_mock) -> None:
    get_store_key_mock.return_value = None
    cosmos_client_mock.return_value = None
    cosmos_client_mock.side_effect = Exception()

    status, message = health_checker.create_state_store_status()

    assert status == StatusEnum.not_ok
    assert message == strings.UNSPECIFIED_ERROR



@patch("services.health_checker.default_credentials")
@patch("services.health_checker.ServiceBusClient")
async def test_get_service_bus_status_responding(service_bus_client_mock, default_credentials) -> None:
    default_credentials.return_value = AsyncMock()
    service_bus_client_mock().get_queue_receiver.__aenter__.return_value = AsyncMock()
    status, message = await health_checker.create_service_bus_status()

    assert status == StatusEnum.ok
    assert message == ""


@patch("services.health_checker.default_credentials")
@patch("services.health_checker.ServiceBusClient")
async def test_get_service_bus_status_not_responding(service_bus_client_mock, default_credentials) -> None:
    default_credentials.return_value = AsyncMock()
    service_bus_client_mock.return_value = None
    service_bus_client_mock.side_effect = ServiceBusConnectionError(message="some message")

    status, message = await health_checker.create_service_bus_status()

    assert status == StatusEnum.not_ok
    assert message == strings.SERVICE_BUS_NOT_RESPONDING


@patch("services.health_checker.default_credentials")
@patch("services.health_checker.ServiceBusClient")
async def test_get_service_bus_status_other_exception(service_bus_client_mock, default_credentials) -> None:
    default_credentials.return_value = AsyncMock()
    service_bus_client_mock.return_value = None
    service_bus_client_mock.side_effect = Exception()

    status, message = await health_checker.create_service_bus_status()

    assert status == StatusEnum.not_ok
    assert message == strings.UNSPECIFIED_ERROR
