import json
from unittest.mock import patch, AsyncMock, Mock
import pytest
import asyncio
from resource_processor.vmss_porter.runner import (
    set_up_config, receive_message, run_porter, invoke_porter_action, get_porter_outputs, check_runners, runner, default_credentials
)
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage, ServiceBusSessionFilter
from azure.servicebus.exceptions import OperationTimeoutError, ServiceBusConnectionError


@pytest.fixture
def mock_service_bus_client():
    with patch("resource_processor.vmss_porter.runner.ServiceBusClient") as mock:
        yield mock


@pytest.fixture
def mock_default_credential():
    with patch("resource_processor.vmss_porter.runner.default_credentials") as mock:
        yield mock


@pytest.fixture
def mock_auto_lock_renewer():
    with patch("resource_processor.vmss_porter.runner.AutoLockRenewer") as mock:
        yield mock


@pytest.fixture
def mock_logger():
    with patch("resource_processor.vmss_porter.runner.logger") as mock:
        yield mock


@pytest.mark.asyncio
@patch("resource_processor.vmss_porter.runner.get_config", return_value={"resource_request_queue": "test_queue", "service_bus_namespace": "test_namespace", "vmss_msi_id": "test_msi_id", "porter_env": {}})
async def test_set_up_config(mock_get_config):
    """Test setting up configuration."""
    config = set_up_config()
    assert config == {"resource_request_queue": "test_queue", "service_bus_namespace": "test_namespace", "vmss_msi_id": "test_msi_id", "porter_env": {}}


async def setup_service_bus_client_and_credential(mock_service_bus_client, mock_default_credential, msi_id):
    mock_credential = AsyncMock()
    mock_default_credential.return_value.__aenter__.return_value = mock_credential
    mock_service_bus_client_instance = mock_service_bus_client.return_value
    return mock_service_bus_client_instance, mock_credential


@pytest.mark.asyncio
@patch("resource_processor.vmss_porter.runner.receive_message")
async def test_runner(mock_receive_message, mock_service_bus_client, mock_default_credential):
    """Test runner with valid MSI ID."""
    mock_service_bus_client_instance, mock_credential = await setup_service_bus_client_and_credential(mock_service_bus_client, mock_default_credential, 'test_msi_id')

    config = {"vmss_msi_id": "test_msi_id", "service_bus_namespace": "test_namespace"}

    await runner(0, config)

    mock_default_credential.assert_called_once_with('test_msi_id')
    mock_service_bus_client.assert_called_once_with("test_namespace", mock_credential)
    mock_receive_message.assert_called_once_with(mock_service_bus_client_instance, config)


@pytest.mark.asyncio
@patch("resource_processor.vmss_porter.runner.receive_message")
async def test_runner_no_msi_id(mock_receive_message, mock_service_bus_client, mock_default_credential):
    """Test runner with no MSI ID."""
    mock_service_bus_client_instance, mock_credential = await setup_service_bus_client_and_credential(mock_service_bus_client, mock_default_credential, None)

    config = {"vmss_msi_id": None, "service_bus_namespace": "test_namespace"}

    await runner(0, config)

    mock_default_credential.assert_called_once_with(None)
    mock_service_bus_client.assert_called_once_with("test_namespace", mock_credential)
    mock_receive_message.assert_called_once_with(mock_service_bus_client_instance, config)


@pytest.mark.asyncio
@patch("resource_processor.vmss_porter.runner.receive_message")
async def test_runner_exception(mock_receive_message, mock_service_bus_client, mock_default_credential):
    """Test runner with an exception."""
    mock_service_bus_client_instance, mock_credential = await setup_service_bus_client_and_credential(mock_service_bus_client, mock_default_credential, 'test_msi_id')
    mock_receive_message.side_effect = Exception("Test Exception")

    config = {"vmss_msi_id": "test_msi_id", "service_bus_namespace": "test_namespace"}

    with pytest.raises(Exception, match="Test Exception"):
        await runner(0, config)

    mock_default_credential.assert_called_once_with('test_msi_id')
    mock_service_bus_client.assert_called_once_with("test_namespace", mock_credential)
    mock_receive_message.assert_called_once_with(mock_service_bus_client_instance, config)


@pytest.mark.asyncio
@patch("resource_processor.vmss_porter.runner.invoke_porter_action", return_value=True)
async def test_receive_message(mock_invoke_porter_action, mock_service_bus_client, mock_auto_lock_renewer):
    mock_service_bus_client_instance = mock_service_bus_client.return_value
    mock_auto_lock_renewer.return_value = AsyncMock()

    mock_receiver = AsyncMock()
    mock_receiver.__aenter__.return_value = mock_receiver
    mock_receiver.__aexit__.return_value = None
    mock_receiver.session.session_id = "test_session_id"
    mock_receiver.__aiter__.return_value = [AsyncMock()]
    mock_receiver.__aiter__.return_value[0] = json.dumps({"id": "test_id", "action": "install", "stepId": "test_step_id", "operationId": "test_operation_id"})

    mock_service_bus_client_instance.get_queue_receiver.return_value.__aenter__.return_value = mock_receiver

    run_once = Mock(side_effect=[True, False])

    config = {"resource_request_queue": "test_queue"}

    await receive_message(mock_service_bus_client_instance, config, keep_running=run_once)
    mock_receiver.complete_message.assert_called_once()
    mock_service_bus_client_instance.get_queue_receiver.assert_called_once_with(queue_name="test_queue", max_wait_time=1, session_id=ServiceBusSessionFilter.NEXT_AVAILABLE)


@pytest.mark.asyncio
async def test_receive_message_unknown_exception(mock_default_credential, mock_auto_lock_renewer, mock_service_bus_client, mock_logger):
    """Test receiving a message with an unknown exception."""
    mock_service_bus_client_instance = mock_service_bus_client.return_value
    mock_auto_lock_renewer.return_value = AsyncMock()

    mock_receiver = AsyncMock()
    mock_receiver.__aenter__.return_value = mock_receiver
    mock_receiver.__aexit__.return_value = None
    mock_receiver.session.session_id = "test_session_id"
    mock_receiver.__aiter__.return_value = [AsyncMock()]
    mock_receiver.__aiter__.return_value[0] = json.dumps({"id": "test_id", "action": "install", "stepId": "test_step_id", "operationId": "test_operation_id"})

    mock_service_bus_client_instance.get_queue_receiver.return_value.__aenter__.return_value = mock_receiver

    run_once = Mock(side_effect=[True, False])

    config = {"resource_request_queue": "test_queue"}

    with patch("resource_processor.vmss_porter.runner.receive_message", side_effect=Exception("Test Exception")):
        await receive_message(mock_service_bus_client_instance, config, keep_running=run_once)
        mock_logger.exception.assert_any_call("Unknown exception. Will retry...")


@pytest.mark.asyncio
@patch("resource_processor.vmss_porter.runner.build_porter_command", return_value=["porter install"])
@patch("resource_processor.vmss_porter.runner.run_porter", return_value=(0, "stdout", "stderr"))
@patch("resource_processor.vmss_porter.runner.service_bus_message_generator", return_value="test_message")
async def test_invoke_porter_action(mock_service_bus_message_generator, mock_run_porter, mock_build_porter_command, mock_service_bus_client):
    """Test invoking a porter action."""
    mock_sb_sender = AsyncMock()
    mock_service_bus_client.get_queue_sender.return_value = mock_sb_sender

    config = {"deployment_status_queue": "test_queue"}
    msg_body = {"id": "test_id", "action": "install", "stepId": "test_step_id", "operationId": "test_operation_id"}

    result = await invoke_porter_action(msg_body, mock_service_bus_client, config)

    assert result is True
    mock_sb_sender.send_messages.assert_called()


@pytest.mark.asyncio
@patch("resource_processor.vmss_porter.runner.build_porter_command", return_value=["porter install"])
@patch("resource_processor.vmss_porter.runner.run_porter", return_value=(1, "", "error"))
@patch("resource_processor.vmss_porter.runner.service_bus_message_generator", return_value="test_message")
async def test_invoke_porter_action_failure(mock_service_bus_message_generator, mock_run_porter, mock_build_porter_command, mock_service_bus_client):
    """Test invoking a porter action with failure."""
    mock_sb_client = AsyncMock(spec=ServiceBusClient)
    mock_sb_sender = AsyncMock()
    mock_sb_client.get_queue_sender.return_value = mock_sb_sender

    config = {"deployment_status_queue": "test_queue"}
    msg_body = {"id": "test_id", "action": "install", "stepId": "test_step_id", "operationId": "test_operation_id"}

    result = await invoke_porter_action(msg_body, mock_sb_client, config)

    assert result is False
    mock_sb_sender.send_messages.assert_called()


@pytest.mark.asyncio
@patch("resource_processor.vmss_porter.runner.build_porter_command", return_value=["porter install"])
@patch("resource_processor.vmss_porter.runner.run_porter", side_effect=[(1, "", "could not find installation"), (0, "", "")])
@patch("resource_processor.vmss_porter.runner.service_bus_message_generator", return_value="test_message")
async def test_invoke_porter_action_upgrade_failure_install_success(mock_service_bus_message_generator, mock_run_porter, mock_build_porter_command, mock_service_bus_client):
    """Test invoking a porter action with upgrade failure and install success."""
    mock_sb_client = AsyncMock(spec=ServiceBusClient)
    mock_sb_sender = AsyncMock()
    mock_sb_client.get_queue_sender.return_value = mock_sb_sender

    config = {"deployment_status_queue": "test_queue"}
    msg_body = {"id": "test_id", "action": "upgrade", "stepId": "test_step_id", "operationId": "test_operation_id"}

    result = await invoke_porter_action(msg_body, mock_sb_client, config)

    assert result is True
    mock_sb_sender.send_messages.assert_called()


@pytest.mark.asyncio
@patch("resource_processor.vmss_porter.runner.build_porter_command", return_value=["porter install"])
@patch("resource_processor.vmss_porter.runner.run_porter", side_effect=[(1, "", "could not find installation"), (1, "", "installation failed")])
@patch("resource_processor.vmss_porter.runner.service_bus_message_generator", return_value="test_message")
async def test_invoke_porter_action_upgrade_failure_install_failure(mock_service_bus_message_generator, mock_run_porter, mock_build_porter_command, mock_service_bus_client):
    """Test invoking a porter action with upgrade and install failure."""
    mock_sb_client = AsyncMock(spec=ServiceBusClient)
    mock_sb_sender = AsyncMock()
    mock_sb_client.get_queue_sender.return_value = mock_sb_sender

    config = {"deployment_status_queue": "test_queue"}
    msg_body = {"id": "test_id", "action": "upgrade", "stepId": "test_step_id", "operationId": "test_operation_id"}

    result = await invoke_porter_action(msg_body, mock_sb_client, config)

    assert result is False
    mock_sb_sender.send_messages.assert_called()


@pytest.mark.asyncio
@patch("resource_processor.vmss_porter.runner.build_porter_command", return_value=["porter install"])
@patch("resource_processor.vmss_porter.runner.run_porter", return_value=(1, "", "could not find installation"))
@patch("resource_processor.vmss_porter.runner.service_bus_message_generator", return_value="test_message")
async def test_invoke_porter_action_uninstall_failure(mock_service_bus_message_generator, mock_run_porter, mock_build_porter_command, mock_service_bus_client):
    """Test invoking a porter action with uninstall failure."""
    mock_sb_client = AsyncMock(spec=ServiceBusClient)
    mock_sb_sender = AsyncMock()
    mock_sb_client.get_queue_sender.return_value = mock_sb_sender

    config = {"deployment_status_queue": "test_queue"}
    msg_body = {"id": "test_id", "action": "uninstall", "stepId": "test_step_id", "operationId": "test_operation_id"}

    result = await invoke_porter_action(msg_body, mock_sb_client, config)

    assert result is True
    mock_sb_sender.send_messages.assert_called()


@pytest.mark.asyncio
@patch("resource_processor.vmss_porter.runner.build_porter_command", return_value=["porter custom-action"])
@patch("resource_processor.vmss_porter.runner.run_porter", return_value=(0, "stdout", "stderr"))
@patch("resource_processor.vmss_porter.runner.service_bus_message_generator", return_value="test_message")
async def test_invoke_porter_action_custom_action(mock_service_bus_message_generator, mock_run_porter, mock_build_porter_command, mock_service_bus_client):
    """Test invoking a porter custom action."""
    mock_sb_client = AsyncMock(spec=ServiceBusClient)
    mock_sb_sender = AsyncMock()
    mock_sb_client.get_queue_sender.return_value = mock_sb_sender

    config = {"deployment_status_queue": "test_queue"}
    msg_body = {"id": "test_id", "action": "custom-action", "stepId": "test_step_id", "operationId": "test_operation_id"}

    result = await invoke_porter_action(msg_body, mock_sb_client, config)

    assert result is True
    mock_sb_sender.send_messages.assert_called()


@pytest.mark.asyncio
@patch("resource_processor.vmss_porter.runner.build_porter_command_for_outputs", return_value=["porter installations output list"])
@patch("resource_processor.vmss_porter.runner.run_porter", return_value=(0, json.dumps([{"name": "output1", "value": "value1"}]), "stderr"))
async def test_get_porter_outputs(mock_run_porter, mock_build_porter_command_for_outputs):
    """Test getting porter outputs."""
    config = {}
    msg_body = {"id": "test_id", "action": "install"}

    success, outputs = await get_porter_outputs(msg_body, config)

    assert success is True
    assert outputs == [{"name": "output1", "value": "value1"}]


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_check_runners(_):
    """Test checking runners."""
    mock_process = Mock()
    mock_process.is_alive.return_value = False
    processes = [mock_process]
    mock_httpserver = AsyncMock()

    run_once = Mock(side_effect=[True, False])

    await check_runners(processes, mock_httpserver, keep_running=run_once)
    mock_httpserver.kill.assert_called_once()
