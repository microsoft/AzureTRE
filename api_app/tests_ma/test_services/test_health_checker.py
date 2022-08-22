from unittest.mock import AsyncMock, MagicMock
import pytest
from azure.core.exceptions import ServiceRequestError
from azure.servicebus.exceptions import ServiceBusConnectionError
from mock import patch

from models.schemas.status import StatusEnum
from resources import strings
from services import health_checker


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


@patch("core.credentials.get_credential_async")
@patch("services.health_checker.ServiceBusClient")
@pytest.mark.asyncio
async def test_get_service_bus_status_responding(service_bus_client_mock, get_credential_async) -> None:
    get_credential_async.return_value = AsyncMock()
    service_bus_client_mock().get_queue_receiver.__aenter__.return_value = AsyncMock()
    status, message = await health_checker.create_service_bus_status()

    assert status == StatusEnum.ok
    assert message == ""


@patch("core.credentials.get_credential_async")
@patch("services.health_checker.ServiceBusClient")
@pytest.mark.asyncio
async def test_get_service_bus_status_not_responding(service_bus_client_mock, get_credential_async) -> None:
    get_credential_async.return_value = AsyncMock()
    service_bus_client_mock.return_value = None
    service_bus_client_mock.side_effect = ServiceBusConnectionError(message="some message")
    status, message = await health_checker.create_service_bus_status()

    assert status == StatusEnum.not_ok
    assert message == strings.SERVICE_BUS_NOT_RESPONDING


@patch("core.credentials.get_credential_async")
@patch("services.health_checker.ServiceBusClient")
@pytest.mark.asyncio
async def test_get_service_bus_status_other_exception(service_bus_client_mock, get_credential_async) -> None:
    get_credential_async.return_value = AsyncMock()
    service_bus_client_mock.return_value = None
    service_bus_client_mock.side_effect = Exception()
    status, message = await health_checker.create_service_bus_status()

    assert status == StatusEnum.not_ok
    assert message == strings.UNSPECIFIED_ERROR


@patch("services.health_checker.ComputeManagementClient")
def test_get_resource_processor_status_healthy(resource_processor_client_mock) -> None:
    resource_processor_client_mock().virtual_machine_scale_set_vms = MagicMock()
    vm_mock = MagicMock()
    vm_mock.instance_id = 'mocked_id'
    resource_processor_client_mock().virtual_machine_scale_set_vms.list = MagicMock(return_value=[vm_mock])

    instance_view_mock = MagicMock()
    instance_view_mock.vm_health.status.code = strings.RESOURCE_PROCESSOR_HEALTHY_MESSAGE
    resource_processor_client_mock().virtual_machine_scale_set_vms.get_instance_view.return_value = instance_view_mock

    status, message = health_checker.create_resource_processor_status()

    assert status == StatusEnum.ok
    assert message == ""


@patch("services.health_checker.ComputeManagementClient")
def test_get_resource_processor_status_not_healthy(resource_processor_client_mock) -> None:
    resource_processor_client_mock().virtual_machine_scale_set_vms = MagicMock()
    vm_mock = MagicMock()
    vm_mock.instance_id = 'mocked_id'
    resource_processor_client_mock().virtual_machine_scale_set_vms.list = MagicMock(return_value=[vm_mock])

    instance_view_mock = MagicMock()
    instance_view_mock.vm_health.status.code = "Unhealthy"
    resource_processor_client_mock().virtual_machine_scale_set_vms.get_instance_view.return_value = instance_view_mock
    status, message = health_checker.create_resource_processor_status()

    assert status == StatusEnum.not_ok
    assert message == strings.RESOURCE_PROCESSOR_GENERAL_ERROR_MESSAGE


@patch("services.health_checker.ComputeManagementClient")
def test_get_resource_processor_status_other_exception(resource_processor_client_mock) -> None:
    resource_processor_client_mock.return_value = None
    resource_processor_client_mock.side_effect = Exception()
    status, message = health_checker.create_resource_processor_status()

    assert status == StatusEnum.not_ok
    assert message == strings.UNSPECIFIED_ERROR
