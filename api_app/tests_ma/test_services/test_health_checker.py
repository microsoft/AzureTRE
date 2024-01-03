import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest
from azure.core.exceptions import ServiceRequestError
from azure.servicebus.exceptions import ServiceBusConnectionError
from mock import patch
from models.schemas.status import StatusEnum
from resources import strings
from services import health_checker

pytestmark = pytest.mark.asyncio


@patch("azure.cosmos.aio.ContainerProxy.query_items", return_value=AsyncMock())
async def test_get_state_store_status_responding(_) -> None:
    status, message = await health_checker.create_state_store_status()

    assert status == StatusEnum.ok
    assert message == ""


@patch("api.dependencies.database.Database.get_container_proxy")
async def test_get_state_store_status_not_responding(container_proxy_mock) -> None:
    container_proxy_mock.return_value = None
    container_proxy_mock.side_effect = ServiceRequestError(message="some message")
    status, message = await health_checker.create_state_store_status()

    assert status == StatusEnum.not_ok
    assert message == strings.STATE_STORE_ENDPOINT_NOT_RESPONDING


@patch("api.dependencies.database.Database.get_container_proxy")
async def test_get_state_store_status_other_exception(container_proxy_mock) -> None:
    container_proxy_mock.return_value = None
    container_proxy_mock.side_effect = Exception()
    status, message = await health_checker.create_state_store_status()

    assert status == StatusEnum.not_ok
    assert message == strings.UNSPECIFIED_ERROR


@patch("core.credentials.get_credential_async_context")
@patch("services.health_checker.ServiceBusClient")
async def test_get_service_bus_status_responding(service_bus_client_mock, get_credential_async_context) -> None:
    get_credential_async_context.return_value = AsyncMock()
    service_bus_client_mock().get_queue_receiver.__aenter__.return_value = AsyncMock()
    status, message = await health_checker.create_service_bus_status(get_credential_async_context)

    assert status == StatusEnum.ok
    assert message == ""


@patch("core.credentials.get_credential_async_context")
@patch("services.health_checker.ServiceBusClient")
async def test_get_service_bus_status_not_responding(service_bus_client_mock, get_credential_async_context) -> None:
    get_credential_async_context.return_value = AsyncMock()
    service_bus_client_mock.return_value = None
    service_bus_client_mock.side_effect = ServiceBusConnectionError(message="some message")
    status, message = await health_checker.create_service_bus_status(get_credential_async_context)

    assert status == StatusEnum.not_ok
    assert message == strings.SERVICE_BUS_NOT_RESPONDING


@patch("core.credentials.get_credential_async_context")
@patch("services.health_checker.ServiceBusClient")
async def test_get_service_bus_status_other_exception(service_bus_client_mock, get_credential_async_context) -> None:
    get_credential_async_context.return_value = AsyncMock()
    service_bus_client_mock.return_value = None
    service_bus_client_mock.side_effect = Exception()
    status, message = await health_checker.create_service_bus_status(get_credential_async_context)

    assert status == StatusEnum.not_ok
    assert message == strings.UNSPECIFIED_ERROR


@patch("core.credentials.get_credential_async_context")
@patch("services.health_checker.ComputeManagementClient")
async def test_get_resource_processor_status_healthy(resource_processor_client_mock, get_credential_async_context) -> None:
    get_credential_async_context.return_value = AsyncMock()
    resource_processor_client_mock().virtual_machine_scale_set_vms.return_value = AsyncMock()
    vm_mock = MagicMock()
    vm_mock.instance_id = 'mocked_id'
    resource_processor_client_mock().virtual_machine_scale_set_vms.list.return_value = AsyncIterator([vm_mock])

    instance_view_mock = MagicMock()
    instance_view_mock.vm_health.status.code = strings.RESOURCE_PROCESSOR_HEALTHY_MESSAGE
    awaited_mock = asyncio.Future()
    awaited_mock.set_result(instance_view_mock)
    resource_processor_client_mock().virtual_machine_scale_set_vms.get_instance_view.return_value = awaited_mock

    status, message = await health_checker.create_resource_processor_status(get_credential_async_context)

    assert status == StatusEnum.ok
    assert message == ""


@patch("core.credentials.get_credential_async_context")
@patch("services.health_checker.ComputeManagementClient", return_value=MagicMock())
async def test_get_resource_processor_status_not_healthy(resource_processor_client_mock, get_credential_async_context) -> None:
    get_credential_async_context.return_value = AsyncMock()

    resource_processor_client_mock().virtual_machine_scale_set_vms.return_value = AsyncMock()
    vm_mock = MagicMock()
    vm_mock.instance_id = 'mocked_id'
    resource_processor_client_mock().virtual_machine_scale_set_vms.list.return_value = AsyncIterator([vm_mock])

    instance_view_mock = MagicMock()
    instance_view_mock.vm_health.status.code = "Unhealthy"
    awaited_mock = asyncio.Future()
    awaited_mock.set_result(instance_view_mock)
    resource_processor_client_mock().virtual_machine_scale_set_vms.get_instance_view.return_value = awaited_mock

    status, message = await health_checker.create_resource_processor_status(get_credential_async_context)

    assert status == StatusEnum.not_ok
    assert message == strings.RESOURCE_PROCESSOR_GENERAL_ERROR_MESSAGE


@patch("core.credentials.get_credential_async_context")
@patch("services.health_checker.ComputeManagementClient")
async def test_get_resource_processor_status_other_exception(resource_processor_client_mock, get_credential_async_context) -> None:
    get_credential_async_context.return_value = AsyncMock()
    resource_processor_client_mock.return_value = None
    resource_processor_client_mock.side_effect = Exception()
    status, message = await health_checker.create_resource_processor_status(get_credential_async_context)

    assert status == StatusEnum.not_ok
    assert message == strings.UNSPECIFIED_ERROR


class AsyncIterator:
    def __init__(self, seq):
        self.iter = iter(seq)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.iter)
        except StopIteration:
            raise StopAsyncIteration
