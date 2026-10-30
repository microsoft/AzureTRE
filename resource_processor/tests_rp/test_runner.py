from azure.core.exceptions import HttpResponseError
from azure.servicebus import ServiceBusSessionFilter
from azure.servicebus.exceptions import SessionLockLostError
from azure.servicebus.aio import ServiceBusClient
from vmss_porter.runner import (
    set_up_config,
    receive_message,
    invoke_porter_action,
    get_porter_outputs,
    check_runners,
    runner,
    run_porter,
    worker_config,
    _cleanup_param_set,
)
import json
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import ANY, patch, AsyncMock, Mock
import pytest
import sys
from pathlib import Path

# Add project root to path to allow imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_service_bus_client():
    with patch("vmss_porter.runner.ServiceBusClient") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_container_client():
    with patch("vmss_porter.runner.ContainerClient") as mock:
        instance = mock.return_value
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        yield mock


@pytest.fixture
def mock_default_credential():
    with patch("vmss_porter.runner.default_credentials") as mock:
        yield mock


@pytest.fixture
def mock_execution_lease():
    execution = AsyncMock()
    execution.read.return_value = {}

    @asynccontextmanager
    async def lease(container, resource_id, describe):
        yield execution

    with patch("vmss_porter.runner.execution_lease", side_effect=lease) as mock:
        mock.execution = execution
        yield mock


@pytest.fixture
def mock_keep_renewed():
    async def renew_until_cancelled(*args, **kwargs):
        await asyncio.Event().wait()

    with patch("vmss_porter.runner.keep_renewed", side_effect=renew_until_cancelled) as mock:
        yield mock


@pytest.fixture
def mock_logger():
    with patch("vmss_porter.runner.logger") as mock:
        yield mock


@pytest.mark.asyncio
@patch(
    "vmss_porter.runner.get_config",
    return_value={
        "resource_request_queue": "test_queue",
        "service_bus_namespace": "test_namespace",
        "vmss_msi_id": "test_msi_id",
        "porter_env": {},
    },
)
async def test_set_up_config(mock_get_config):
    """Test setting up configuration."""
    config = set_up_config()
    assert config == {
        "resource_request_queue": "test_queue",
        "service_bus_namespace": "test_namespace",
        "vmss_msi_id": "test_msi_id",
        "porter_env": {},
    }


async def setup_service_bus_client_and_credential(mock_service_bus_client, mock_default_credential, msi_id):
    mock_credential = AsyncMock()
    mock_default_credential.return_value.__aenter__ = AsyncMock(return_value=mock_credential)
    mock_default_credential.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_service_bus_client_instance = mock_service_bus_client.return_value
    mock_service_bus_client.return_value.__aenter__ = AsyncMock(return_value=mock_service_bus_client_instance)
    mock_service_bus_client.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_service_bus_client_instance, mock_credential


@pytest.mark.asyncio
@patch("vmss_porter.runner.receive_message")
async def test_runner(mock_receive_message, mock_service_bus_client, mock_default_credential):
    """Test runner with valid MSI ID."""
    mock_service_bus_client_instance, mock_credential = await setup_service_bus_client_and_credential(
        mock_service_bus_client, mock_default_credential, "test_msi_id"
    )

    config = {
        "vmss_msi_id": "test_msi_id",
        "service_bus_namespace": "test_namespace",
        "porter_env": {"HOME": "/root"},
        "mgmt_blob_url": "https://mgmt",
    }

    await runner(0, config)

    mock_default_credential.assert_called_once_with("test_msi_id")
    mock_service_bus_client.assert_called_once_with("test_namespace", mock_credential)
    mock_receive_message.assert_called_once_with(mock_service_bus_client_instance, worker_config(0, config), ANY)

    # Verify context manager entered and exited cleanly
    mock_default_credential.return_value.__aenter__.assert_awaited_once()
    mock_default_credential.return_value.__aexit__.assert_awaited_once()
    mock_service_bus_client.return_value.__aenter__.assert_awaited_once()
    mock_service_bus_client.return_value.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
@patch("vmss_porter.runner.receive_message")
async def test_runner_no_msi_id(mock_receive_message, mock_service_bus_client, mock_default_credential):
    """Test runner with no MSI ID."""
    mock_service_bus_client_instance, mock_credential = await setup_service_bus_client_and_credential(
        mock_service_bus_client, mock_default_credential, None
    )

    config = {
        "vmss_msi_id": None,
        "service_bus_namespace": "test_namespace",
        "porter_env": {"HOME": "/root"},
        "mgmt_blob_url": "https://mgmt",
    }

    await runner(0, config)

    mock_default_credential.assert_called_once_with(None)
    mock_service_bus_client.assert_called_once_with("test_namespace", mock_credential)
    mock_receive_message.assert_called_once_with(mock_service_bus_client_instance, worker_config(0, config), ANY)

    # Verify context manager entered and exited cleanly
    mock_default_credential.return_value.__aenter__.assert_awaited_once()
    mock_default_credential.return_value.__aexit__.assert_awaited_once()
    mock_service_bus_client.return_value.__aenter__.assert_awaited_once()
    mock_service_bus_client.return_value.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
@patch("vmss_porter.runner.receive_message")
async def test_runner_exception(mock_receive_message, mock_service_bus_client, mock_default_credential):
    """Test runner with an exception."""
    mock_service_bus_client_instance, mock_credential = await setup_service_bus_client_and_credential(
        mock_service_bus_client, mock_default_credential, "test_msi_id"
    )
    mock_receive_message.side_effect = Exception("Test Exception")

    config = {
        "vmss_msi_id": "test_msi_id",
        "service_bus_namespace": "test_namespace",
        "porter_env": {"HOME": "/root"},
        "mgmt_blob_url": "https://mgmt",
    }

    with pytest.raises(Exception, match="Test Exception"):
        await runner(0, config)

    mock_default_credential.assert_called_once_with("test_msi_id")
    mock_service_bus_client.assert_called_once_with("test_namespace", mock_credential)
    mock_receive_message.assert_called_once_with(mock_service_bus_client_instance, worker_config(0, config), ANY)

    # Verify context manager entered and exited cleanly, even on exception
    mock_default_credential.return_value.__aenter__.assert_awaited_once()
    mock_default_credential.return_value.__aexit__.assert_awaited_once()
    mock_service_bus_client.return_value.__aenter__.assert_awaited_once()
    mock_service_bus_client.return_value.__aexit__.assert_awaited_once()


def test_each_worker_has_its_own_azure_cli_folder():
    # Two workers that share one folder can read a profile file that the other one writes.
    config = {"porter_env": {"HOME": "/root", "PATH": "/bin"}}

    first, second = worker_config(0, config), worker_config(1, config)

    assert first["porter_env"]["AZURE_CONFIG_DIR"] == "/root/.azure-worker-0"
    assert second["porter_env"]["AZURE_CONFIG_DIR"] == "/root/.azure-worker-1"
    assert first["porter_env"]["PATH"] == "/bin"
    assert "AZURE_CONFIG_DIR" not in config["porter_env"]


@pytest.mark.asyncio
async def test_default_credentials_closes_real_credential_on_exception(mock_service_bus_client):
    mock_credential = AsyncMock()
    mock_service_bus_client_instance = mock_service_bus_client.return_value
    mock_service_bus_client.return_value.__aenter__.return_value = mock_service_bus_client_instance

    with (
        patch("vmss_porter.runner.DefaultAzureCredential", return_value=mock_credential),
        patch("vmss_porter.runner.receive_message", side_effect=Exception("Test Exception")),
    ):
        config = {
            "vmss_msi_id": "test_msi_id",
            "service_bus_namespace": "test_namespace",
            "porter_env": {"HOME": "/root"},
            "mgmt_blob_url": "https://mgmt",
        }

        with pytest.raises(Exception, match="Test Exception"):
            await runner(0, config)

    mock_credential.close.assert_awaited_once()


@pytest.mark.asyncio
@patch("vmss_porter.runner.run_step", return_value=True)
async def test_receive_message(
    mock_run_step, mock_service_bus_client, mock_execution_lease, mock_keep_renewed, mock_logger
):
    mock_service_bus_client_instance = mock_service_bus_client.return_value

    mock_receiver = AsyncMock()
    mock_receiver.__aenter__.return_value = mock_receiver
    mock_receiver.__aexit__.return_value = None
    mock_receiver.session.session_id = "test_session_id"
    mock_receiver.__aiter__.return_value = [AsyncMock()]
    mock_receiver.__aiter__.return_value[0] = json.dumps(
        {
            "id": "test_id",
            "action": "install",
            "stepId": "test_step_id",
            "operationId": "test_operation_id",
            "name": "test_bundle",
            "version": "1.0.0",
            "parameters": {"smtpPassword": "synthetic-password-not-for-logs"},
        }
    )

    mock_service_bus_client_instance.get_queue_receiver.return_value.__aenter__.return_value = mock_receiver

    run_once = Mock(side_effect=[True, False])

    config = {"resource_request_queue": "test_queue"}

    await receive_message(mock_service_bus_client_instance, config, AsyncMock(), keep_running=run_once)
    mock_receiver.complete_message.assert_awaited_once()
    assert "synthetic-password-not-for-logs" not in str(mock_logger.mock_calls)
    mock_service_bus_client_instance.get_queue_receiver.assert_called_once_with(
        queue_name="test_queue", max_wait_time=1, session_id=ServiceBusSessionFilter.NEXT_AVAILABLE
    )


@pytest.mark.asyncio
async def test_receive_message_bad_json(mock_service_bus_client, mock_execution_lease, mock_keep_renewed):
    mock_service_bus_client_instance = mock_service_bus_client.return_value

    mock_receiver = AsyncMock()
    mock_receiver.__aenter__.return_value = mock_receiver
    mock_receiver.__aexit__.return_value = None
    mock_receiver.session.session_id = "test_session_id"
    mock_receiver.__aiter__.return_value = ["invalid_json_string"]

    mock_service_bus_client_instance.get_queue_receiver.return_value.__aenter__.return_value = mock_receiver

    run_once = Mock(side_effect=[True, False])

    config = {"resource_request_queue": "test_queue"}

    await receive_message(mock_service_bus_client_instance, config, AsyncMock(), keep_running=run_once)
    mock_receiver.dead_letter_message.assert_awaited_once()
    dead_letter_args, dead_letter_kwargs = mock_receiver.dead_letter_message.await_args
    assert dead_letter_args == ("invalid_json_string",)
    assert dead_letter_kwargs["reason"] == "InvalidJSON"
    assert dead_letter_kwargs["error_description"]
    mock_receiver.complete_message.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message, expected_log",
    [
        ("invalid_json_string", "Failed to dead-letter malformed message"),
        ("null", "Failed to dead-letter invalid resource request message"),
    ],
)
async def test_receive_message_dead_letter_failure_is_logged(
    message, expected_log, mock_service_bus_client, mock_execution_lease, mock_keep_renewed, mock_logger
):
    mock_service_bus_client_instance = mock_service_bus_client.return_value

    mock_receiver = AsyncMock()
    mock_receiver.__aenter__.return_value = mock_receiver
    mock_receiver.__aexit__.return_value = None
    mock_receiver.session.session_id = "test_session_id"
    mock_receiver.__aiter__.return_value = [message]
    mock_receiver.dead_letter_message.side_effect = RuntimeError("lock lost")

    mock_service_bus_client_instance.get_queue_receiver.return_value.__aenter__.return_value = mock_receiver

    run_once = Mock(side_effect=[True, False])
    config = {"resource_request_queue": "test_queue"}

    with patch("vmss_porter.runner.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await receive_message(mock_service_bus_client_instance, config, AsyncMock(), keep_running=run_once)

    mock_sleep.assert_awaited_once_with(10)

    assert mock_logger.exception.call_args_list == [
        ((expected_log,), {}),
        (("Unknown exception. Will retry...",), {}),
    ]
    mock_receiver.complete_message.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message, error_description",
    [
        ("null", "Resource request message must be a JSON object"),
        ("[]", "Resource request message must be a JSON object"),
        ('"text"', "Resource request message must be a JSON object"),
        (
            '{"id": "test_id"}',
            "Resource request message is missing fields: ['action', 'name', 'operationId', 'parameters', 'stepId', 'version']",
        ),
        (
            '{"id": "test_id", "action": [], "stepId": "test_step_id", "operationId": "test_operation_id", "name": "test_bundle", "version": "1.0.0", "parameters": {}}',
            "Resource request message has invalid field types: ['action']",
        ),
        (
            '{"id": "test_id", "action": "install", "stepId": "test_step_id", "operationId": "test_operation_id", "name": "test_bundle", "version": "1.0.0", "parameters": null}',
            "Resource request message has invalid field types: ['parameters']",
        ),
        (
            '{"id": "test_id", "action": "install", "stepId": "test_step_id", "operationId": "test_operation_id", "name": "test_bundle", "version": "1.0.0", "parameters": {}, "user": []}',
            "Resource request message has invalid field types: ['user']",
        ),
    ],
)
async def test_receive_message_invalid_json_structure(
    message, error_description, mock_service_bus_client, mock_execution_lease, mock_keep_renewed
):
    mock_service_bus_client_instance = mock_service_bus_client.return_value

    mock_receiver = AsyncMock()
    mock_receiver.__aenter__.return_value = mock_receiver
    mock_receiver.__aexit__.return_value = None
    mock_receiver.session.session_id = "test_session_id"
    mock_receiver.__aiter__.return_value = [message]

    mock_service_bus_client_instance.get_queue_receiver.return_value.__aenter__.return_value = mock_receiver

    run_once = Mock(side_effect=[True, False])
    config = {"resource_request_queue": "test_queue"}

    await receive_message(mock_service_bus_client_instance, config, AsyncMock(), keep_running=run_once)

    mock_receiver.dead_letter_message.assert_awaited_once_with(
        message,
        reason="InvalidResourceRequest",
        error_description=error_description,
    )
    mock_receiver.complete_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_receive_message_unknown_exception(
    mock_execution_lease, mock_keep_renewed, mock_service_bus_client, mock_logger
):
    """Test receiving a message with an unknown exception."""
    mock_service_bus_client_instance = mock_service_bus_client.return_value

    mock_receiver = AsyncMock()
    mock_receiver.__aenter__.return_value = mock_receiver
    mock_receiver.__aexit__.return_value = None
    mock_receiver.session.session_id = "test_session_id"
    mock_receiver.__aiter__.return_value = [AsyncMock()]
    mock_receiver.__aiter__.return_value[0] = json.dumps(
        {
            "id": "test_id",
            "action": "install",
            "stepId": "test_step_id",
            "operationId": "test_operation_id",
            "name": "test_bundle",
            "version": "1.0.0",
            "parameters": {},
        }
    )

    mock_service_bus_client_instance.get_queue_receiver.return_value.__aenter__.return_value = mock_receiver

    run_once = Mock(side_effect=[True, False])

    config = {"resource_request_queue": "test_queue"}

    with (
        patch("vmss_porter.runner.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        patch("vmss_porter.runner.receive_message", side_effect=Exception("Test Exception")),
    ):
        await receive_message(mock_service_bus_client_instance, config, AsyncMock(), keep_running=run_once)
        mock_logger.exception.assert_any_call("Unknown exception. Will retry...")
        mock_sleep.assert_awaited_once_with(10)


@pytest.mark.asyncio
@patch("vmss_porter.runner.build_porter_command", return_value=([["porter", "install"]], None, "tre-params-test", None))
@patch("vmss_porter.runner.run_porter", return_value=(0, "stdout", "stderr"))
@patch("vmss_porter.runner.service_bus_message_generator", return_value="test_message")
async def test_invoke_porter_action(
    mock_service_bus_message_generator, mock_run_porter, mock_build_porter_command, mock_service_bus_client
):
    """Test invoking a porter action."""
    mock_sb_sender = AsyncMock()
    mock_service_bus_client.get_queue_sender.return_value = mock_sb_sender

    config = {"deployment_status_queue": "test_queue"}
    msg_body = {"id": "test_id", "action": "install", "stepId": "test_step_id", "operationId": "test_operation_id"}

    result = await invoke_porter_action(msg_body, mock_service_bus_client, config)

    assert result is True
    mock_sb_sender.send_messages.assert_called()


@pytest.mark.asyncio
@patch("vmss_porter.runner.build_porter_command", return_value=([["porter", "install"]], None, "tre-params-test", None))
@patch("vmss_porter.runner.run_porter", return_value=(1, "", "error"))
@patch("vmss_porter.runner.service_bus_message_generator", return_value="test_message")
async def test_invoke_porter_action_failure(
    mock_service_bus_message_generator, mock_run_porter, mock_build_porter_command, mock_service_bus_client
):
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
@patch("vmss_porter.runner._cleanup_param_set", side_effect=RuntimeError("cleanup failed"))
@patch(
    "vmss_porter.runner.build_porter_command",
    return_value=([["porter", "install"]], "/tmp/params.json", "tre-params-test", None),
)
@patch("vmss_porter.runner.run_porter", return_value=(1, "", "error"))
@patch("vmss_porter.runner.service_bus_message_generator", return_value="test_message")
async def test_invoke_porter_action_cleanup_error_is_non_blocking(
    mock_service_bus_message_generator,
    mock_run_porter,
    mock_build_porter_command,
    mock_cleanup_param_set,
    mock_service_bus_client,
):
    """Cleanup exceptions should not mask porter command failure handling."""
    mock_sb_client = AsyncMock(spec=ServiceBusClient)
    mock_sb_sender = AsyncMock()
    mock_sb_client.get_queue_sender.return_value = mock_sb_sender

    config = {"deployment_status_queue": "test_queue"}
    msg_body = {"id": "test_id", "action": "install", "stepId": "test_step_id", "operationId": "test_operation_id"}

    result = await invoke_porter_action(msg_body, mock_sb_client, config)

    assert result is False
    mock_cleanup_param_set.assert_awaited_once()
    mock_sb_sender.send_messages.assert_called()


@pytest.mark.asyncio
@patch("vmss_porter.runner.build_porter_command", return_value=([["porter", "install"]], None, "tre-params-test", None))
@patch("vmss_porter.runner.run_porter", return_value=(1, "", "could not find installation"))
@patch("vmss_porter.runner.service_bus_message_generator", return_value="test_message")
async def test_invoke_porter_action_upgrade_failure(
    mock_service_bus_message_generator, mock_run_porter, mock_build_porter_command, mock_service_bus_client
):
    """Test invoking a porter action with upgrade failure."""
    mock_sb_client = AsyncMock(spec=ServiceBusClient)
    mock_sb_sender = AsyncMock()
    mock_sb_client.get_queue_sender.return_value = mock_sb_sender

    config = {"deployment_status_queue": "test_queue"}
    msg_body = {"id": "test_id", "action": "upgrade", "stepId": "test_step_id", "operationId": "test_operation_id"}

    result = await invoke_porter_action(msg_body, mock_sb_client, config)

    assert result is False
    mock_sb_sender.send_messages.assert_called()


@pytest.mark.asyncio
@patch("vmss_porter.runner.build_porter_command", return_value=([["porter", "install"]], None, "tre-params-test", None))
@patch(
    "vmss_porter.runner.run_porter",
    side_effect=[(1, "", "could not find installation"), (1, "", "installation failed")],
)
@patch("vmss_porter.runner.service_bus_message_generator", return_value="test_message")
async def test_invoke_porter_action_upgrade_failure_install_failure(
    mock_service_bus_message_generator, mock_run_porter, mock_build_porter_command, mock_service_bus_client
):
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
@pytest.mark.parametrize(
    "action, expected_status",
    [
        ("install", "deployment_failed"),
        ("upgrade", "updating_failed"),
        ("uninstall", "deleting_failed"),
        ("custom-action", "action_failed"),
    ],
)
@pytest.mark.parametrize(
    "error",
    [
        (
            "could not find installation /test_id: could not read storage schema document: "
            + "rpc error: code = DeadlineExceeded desc = server selection error: context deadline exceeded"
        ),
        "could not find installation /test_id: installation does not exist",
        "",
        None,
    ],
    ids=["storage-timeout", "missing-installation", "empty-error", "no-error"],
)
async def test_invoke_porter_action_nonzero_exit_without_confirmed_absence_reports_failure(
    action, expected_status, error
):
    sender = AsyncMock()
    client = Mock()
    client.get_queue_sender.return_value = sender
    config = {"deployment_status_queue": "test_queue"}
    msg_body = {"id": "test_id", "action": action, "stepId": "test_step_id", "operationId": "test_operation_id"}

    with (
        patch("vmss_porter.runner.build_porter_command", return_value=([["porter", action]], None, "params", None)),
        patch("vmss_porter.runner.run_porter", return_value=(1, "", error)),
        patch("vmss_porter.runner.run_command_helper", return_value=(1, None, "Storage is unavailable")) as lookup,
        patch("vmss_porter.runner.get_porter_outputs", return_value=(True, {})) as outputs,
    ):
        result = await invoke_porter_action(msg_body, client, config)

    assert result is False
    outputs.assert_not_awaited()
    assert sender.send_messages.await_count == 2
    final_status = json.loads(str(sender.send_messages.call_args.args[0]))
    assert final_status["status"] == expected_status
    assert (error or "Porter exited with code 1 and no error output.") in final_status["message"]
    if action == "uninstall" and "could not find installation" in (error or ""):
        lookup.assert_awaited_once()
    else:
        lookup.assert_not_awaited()


@pytest.mark.asyncio
@patch(
    "vmss_porter.runner.build_porter_command",
    return_value=([["porter", "custom-action"]], None, "tre-params-test", None),
)
@patch("vmss_porter.runner.run_porter", return_value=(0, "stdout", "stderr"))
@patch("vmss_porter.runner.service_bus_message_generator", return_value="test_message")
async def test_invoke_porter_action_custom_action(
    mock_service_bus_message_generator, mock_run_porter, mock_build_porter_command, mock_service_bus_client
):
    """Test invoking a porter custom action."""
    mock_sb_client = AsyncMock(spec=ServiceBusClient)
    mock_sb_sender = AsyncMock()
    mock_sb_client.get_queue_sender.return_value = mock_sb_sender

    config = {"deployment_status_queue": "test_queue"}
    msg_body = {
        "id": "test_id",
        "action": "custom-action",
        "stepId": "test_step_id",
        "operationId": "test_operation_id",
    }

    result = await invoke_porter_action(msg_body, mock_sb_client, config)

    assert result is True
    mock_sb_sender.send_messages.assert_called()


@pytest.mark.asyncio
@patch("vmss_porter.runner.os.unlink")
@patch("vmss_porter.runner.run_command_helper", new_callable=AsyncMock)
async def test_cleanup_param_set_is_best_effort(mock_run_command_helper, mock_unlink):
    """Cleanup deletes the parameter set without logging errors and unlinks temp files."""
    mock_run_command_helper.return_value = (1, None, "not found")
    config = {"porter_env": {}}

    await _cleanup_param_set("tre-params-test", "/tmp/params.json", "/tmp/installation.json", config)

    # The parameter set delete must be best-effort (log_error=False) since it may never have been applied
    mock_run_command_helper.assert_awaited_once_with(
        ["porter", "parameters", "delete", "tre-params-test"], config, "Delete parameter set", log_error=False
    )
    # Both temp files should be removed
    mock_unlink.assert_any_call("/tmp/params.json")
    mock_unlink.assert_any_call("/tmp/installation.json")


@pytest.mark.asyncio
@patch("vmss_porter.runner.os.unlink")
@patch("vmss_porter.runner.run_command_helper", new_callable=AsyncMock)
async def test_cleanup_param_set_no_param_file(mock_run_command_helper, mock_unlink):
    """When no parameter set file exists, no delete command runs but the installation file is still removed."""
    config = {"porter_env": {}}

    await _cleanup_param_set("tre-params-test", None, "/tmp/installation.json", config)

    mock_run_command_helper.assert_not_awaited()
    mock_unlink.assert_called_once_with("/tmp/installation.json")


@pytest.mark.asyncio
@pytest.mark.parametrize("delete_error", [OSError("cannot start porter"), asyncio.CancelledError()])
async def test_cleanup_param_set_removes_files_when_delete_raises(tmp_path, delete_error):
    parameter_file = tmp_path / "parameters.json"
    installation_file = tmp_path / "installation.json"
    parameter_file.write_text("parameter references")
    value_directory = tmp_path / "parameters.json.values"
    value_directory.mkdir(mode=0o700)
    (value_directory / "value").write_text("secret value")
    installation_file.write_text("installation")

    with patch("vmss_porter.runner.run_command_helper", new_callable=AsyncMock, side_effect=delete_error):
        if isinstance(delete_error, asyncio.CancelledError):
            with pytest.raises(asyncio.CancelledError):
                await _cleanup_param_set("test", str(parameter_file), str(installation_file), {})
        else:
            await _cleanup_param_set("test", str(parameter_file), str(installation_file), {})

    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
@patch("vmss_porter.runner.os.unlink", side_effect=[OSError("permission denied"), None])
@patch("vmss_porter.runner.run_command_helper", new_callable=AsyncMock)
async def test_cleanup_param_set_attempts_both_files(mock_run_command_helper, mock_unlink):
    await _cleanup_param_set("test", "/tmp/parameters.json", "/tmp/installation.json", {})

    assert mock_unlink.call_count == 2
    mock_unlink.assert_any_call("/tmp/installation.json")


@pytest.mark.asyncio
@patch("vmss_porter.runner.run_command_helper")
async def test_run_porter_success(mock_run_command_helper):
    """Test run_porter function with successful command execution for all steps."""
    config = {
        "azure_environment": "AzureCloud",
        "vmss_msi_id": "msi_id",
        "registry_server": "myregistry.azurecr.io",
        "porter_env": {},
    }
    command = [["porter", "install", "test_installation"]]

    # Mock successful execution of all commands - need more responses for the multiple commands now
    mock_run_command_helper.side_effect = [
        (0, "azure cloud set output", None),  # Azure cloud set succeeds
        (0, "azure login output", None),  # Azure login succeeds
        (0, "acr login output", None),  # ACR login succeeds
        (0, "porter cred output 1", None),  # Porter credential set 1 succeeds
        (0, "porter cred output 2", None),  # Porter credential set 2 succeeds
        (0, "porter command output", None),  # Porter command succeeds
    ]

    returncode, stdout, stderr = await run_porter(command, config)

    assert returncode == 0
    assert stdout == "porter command output"
    assert stderr is None
    assert mock_run_command_helper.call_count == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["install", "upgrade", "uninstall", "start"])
async def test_parameter_discovery_failure_stops_before_porter_action(tmp_path, action):
    sender = AsyncMock()
    client = Mock()
    client.get_queue_sender.return_value = sender
    msg = {
        "id": "resource",
        "action": action,
        "operationId": "operation",
        "stepId": "step",
        "name": "test-bundle",
        "version": "1.0.0",
        "parameters": {"test": "current-value"},
    }
    config = {"deployment_status_queue": "test", "registry_server": "test.azurecr.io"}
    with (
        patch("helpers.commands.get_porter_parameter_keys", return_value=None),
        patch("helpers.commands.tempfile.tempdir", str(tmp_path)),
        patch(
            "vmss_porter.runner.run_porter", new_callable=AsyncMock, return_value=(1, None, "synthetic failure")
        ) as run,
    ):
        result = await invoke_porter_action(msg, client, config)

    assert result is False
    run.assert_not_awaited()
    assert list(tmp_path.iterdir()) == []
    status = json.loads(str(sender.send_messages.call_args.args[0]))
    assert "failed" in status["status"]
    assert "Cannot read bundle parameters" in status["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["uninstall", "start"])
async def test_run_porter_blocks_legacy_overrides_before_applying_parameters(action):
    config = {"azure_environment": "AzureCloud", "vmss_msi_id": "msi", "registry_server": "registry.azurecr.io"}
    action_command = (
        ["porter", "uninstall", "resource"]
        if action == "uninstall"
        else ["porter", "invoke", "--action", action, "resource"]
    )
    commands = [["porter", "parameters", "apply", "/tmp/parameters.json"], action_command]
    responses = [(0, None, None)] * 5 + [
        (0, '[{"name":"resource"}]', None),
        (
            0,
            json.dumps(
                {
                    "name": "resource",
                    "status": {"runId": "old-run"},
                    "parameters": {"delete_backups_on_uninstall": True},
                }
            ),
            None,
        ),
    ]
    with patch("vmss_porter.runner.run_command_helper", new_callable=AsyncMock, side_effect=responses) as command:
        code, stdout, error = await run_porter(commands, config, parameter_check_installation="resource")

    assert code != 0
    assert stdout is None
    assert "Upgrade this resource" in error
    assert "legacy Porter parameter overrides" in error
    assert all(call.args[0] not in commands for call in command.await_args_list)
    assert all(call.kwargs.get("log_output") is False for call in command.await_args_list[-2:])


@pytest.mark.asyncio
@pytest.mark.parametrize("installation", [None, {"name": "resource", "status": {"runId": "new-run"}, "parameters": {}}])
async def test_run_porter_allows_missing_or_migrated_installation(installation):
    config = {"azure_environment": "AzureCloud", "vmss_msi_id": "msi", "registry_server": "registry.azurecr.io"}
    commands = [["porter", "uninstall", "resource"]]
    responses = [(0, None, None)] * 5
    if installation is None:
        responses.append((0, "[]", None))
    else:
        responses.extend([(0, '[{"name":"resource"}]', None), (0, json.dumps(installation), None)])
    responses.append((0, "action completed", None))

    with patch("vmss_porter.runner.run_command_helper", new_callable=AsyncMock, side_effect=responses) as command:
        result = await run_porter(commands, config, parameter_check_installation="resource")

    assert result == (0, "action completed", None)
    assert command.await_args_list[-1].args[0] == commands[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "inspection_responses",
    [
        [(1, None, "secret diagnostic")],
        [(0, "not json", None)],
        [(0, "{}", None)],
        [(0, '[{"name":"wrong-resource"}]', None)],
        [(0, '[{"name":"resource"}]', None), (1, None, "secret diagnostic")],
        [(0, '[{"name":"resource"}]', None), (0, "not json", None)],
        [(0, '[{"name":"resource"}]', None), (0, '{"name":"wrong-resource"}', None)],
        [(0, '[{"name":"resource"}]', None), (0, '{"name":"resource","parameters":[]}', None)],
        [(0, '[{"name":"resource"}]', None), (0, '{"name":"resource","parameters":{}}', None)],
    ],
)
async def test_run_porter_stops_when_parameter_inspection_is_inconclusive(inspection_responses):
    config = {"azure_environment": "AzureCloud", "vmss_msi_id": "msi", "registry_server": "registry.azurecr.io"}
    action = ["porter", "uninstall", "resource"]
    with patch(
        "vmss_porter.runner.run_command_helper",
        new_callable=AsyncMock,
        side_effect=[(0, None, None)] * 5 + inspection_responses,
    ) as command:
        code, _, error = await run_porter([action], config, parameter_check_installation="resource")

    assert code != 0
    assert error
    assert "secret diagnostic" not in error
    assert all(call.args[0] != action for call in command.await_args_list)


@pytest.mark.asyncio
async def test_invoke_porter_action_reports_legacy_guard_and_cleans_up(tmp_path):
    parameters = tmp_path / "parameters.json"
    parameters.write_text("secret")
    action = ["porter", "uninstall", "resource"]
    config = {
        "azure_environment": "AzureCloud",
        "vmss_msi_id": "msi",
        "registry_server": "registry.azurecr.io",
        "deployment_status_queue": "status",
    }
    msg_body = {"id": "resource", "action": "uninstall", "operationId": "operation", "stepId": "step"}
    sender = AsyncMock()
    client = Mock()
    client.get_queue_sender.return_value = sender
    responses = [(0, None, None)] * 5 + [
        (0, '[{"name":"resource"}]', None),
        (0, '{"name":"resource","status":{"runId":"old-run"},"parameters":{"backup":true}}', None),
        (1, None, "not applied"),
    ]
    with (
        patch(
            "vmss_porter.runner.build_porter_command", return_value=([action], str(parameters), "test-parameters", None)
        ),
        patch("vmss_porter.runner.run_command_helper", new_callable=AsyncMock, side_effect=responses) as command,
    ):
        result = await invoke_porter_action(msg_body, client, config)

    assert result is False
    assert not parameters.exists()
    assert all(call.args[0] != action for call in command.await_args_list)
    final_status = json.loads(str(sender.send_messages.call_args.args[0]))
    assert final_status["status"] == "deleting_failed"
    assert "Upgrade this resource" in final_status["message"]


@pytest.mark.asyncio
async def test_uninstall_storage_failure_after_parameter_check_preserves_failure(tmp_path):
    parameters = tmp_path / "parameters.json"
    installation = tmp_path / "installation.json"
    parameters.write_text("parameter references")
    installation.write_text("installation document")
    action = ["porter", "uninstall", "resource"]
    config = {
        "azure_environment": "AzureCloud",
        "vmss_msi_id": "msi",
        "registry_server": "registry.azurecr.io",
        "deployment_status_queue": "status",
    }
    msg_body = {"id": "resource", "action": "uninstall", "operationId": "operation", "stepId": "step"}
    sender = AsyncMock()
    client = Mock()
    client.get_queue_sender.return_value = sender
    error = "could not find installation /resource: could not read storage schema document: DeadlineExceeded"
    responses = [(0, None, None)] * 5 + [
        (0, '[{"name":"resource"}]', None),
        (0, '{"name":"resource","status":{"runId":"old-run"},"parameters":{}}', None),
        (1, None, error),
        (0, None, None),
        (1, None, "Storage is still unavailable"),
    ]
    with (
        patch(
            "vmss_porter.runner.build_porter_command",
            return_value=([action], str(parameters), "test-parameters", str(installation)),
        ),
        patch("vmss_porter.runner.run_command_helper", new_callable=AsyncMock, side_effect=responses) as command,
        patch("vmss_porter.runner.get_porter_outputs") as outputs,
    ):
        result = await invoke_porter_action(msg_body, client, config)

    assert result is False
    assert not parameters.exists()
    assert not installation.exists()
    assert command.await_args_list[-3].args[0] == action
    assert command.await_args_list[-2].args[0] == ["porter", "parameters", "delete", "test-parameters"]
    assert command.await_args_list[-1].args[0] == [
        "porter",
        "installations",
        "list",
        "--name",
        "resource",
        "--output",
        "json",
        "--verbosity",
        "error",
    ]
    outputs.assert_not_awaited()
    final_status = json.loads(str(sender.send_messages.call_args.args[0]))
    assert final_status["status"] == "deleting_failed"
    assert error in final_status["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "confirmation, expected_success",
    [
        pytest.param((0, "[]", None), True, id="confirmed-absent"),
        pytest.param((0, '[{"name":"resource"}]', None), False, id="installation-exists"),
        pytest.param((0, '[{"name":"another-resource"}]', None), False, id="unexpected-installation"),
        pytest.param((1, "[]", "Storage is unavailable"), False, id="failed-empty-lookup"),
        pytest.param((0, "invalid JSON", None), False, id="invalid-json"),
        pytest.param((0, "{}", None), False, id="object-response"),
        pytest.param((0, "null", None), False, id="null-response"),
        pytest.param((0, "", None), False, id="empty-output"),
        pytest.param((0, None, None), False, id="no-output"),
        pytest.param(RuntimeError("Lookup failed"), False, id="lookup-exception"),
        pytest.param(TimeoutError(), False, id="lookup-timeout"),
        pytest.param(asyncio.CancelledError(), None, id="cancelled-lookup"),
    ],
)
async def test_uninstall_missing_installation_requires_fresh_confirmation(tmp_path, confirmation, expected_success):
    parameters = tmp_path / "parameters.json"
    installation = tmp_path / "installation.json"
    parameters.write_text("parameter references")
    installation.write_text("installation document")
    action = ["porter", "uninstall", "resource"]
    config = {
        "azure_environment": "AzureCloud",
        "vmss_msi_id": "msi",
        "registry_server": "registry.azurecr.io",
        "deployment_status_queue": "status",
    }
    message = {"id": "resource", "action": "uninstall", "operationId": "operation", "stepId": "step"}
    sender = AsyncMock()
    client = Mock()
    client.get_queue_sender.return_value = sender
    error = "could not find installation /resource: installation does not exist"
    # The parameter check already saw an empty list. It cannot replace the fresh
    # lookup after uninstall fails, because storage availability can change.
    responses = [(0, None, None)] * 5 + [
        (0, "[]", None),
        (1, None, error),
        (0, None, None),
        confirmation,
    ]
    with (
        patch(
            "vmss_porter.runner.build_porter_command",
            return_value=([action], str(parameters), "test-parameters", str(installation)),
        ),
        patch("vmss_porter.runner.run_command_helper", new_callable=AsyncMock, side_effect=responses) as command,
        patch("vmss_porter.runner.get_porter_outputs") as outputs,
    ):
        if expected_success is None:
            with pytest.raises(asyncio.CancelledError):
                await invoke_porter_action(message, client, config)
        else:
            result = await invoke_porter_action(message, client, config)
            assert result is expected_success

    assert not parameters.exists()
    assert not installation.exists()
    assert command.await_args_list[-3].args[0] == action
    assert command.await_args_list[-2].args[0] == ["porter", "parameters", "delete", "test-parameters"]
    assert command.await_args_list[-1].args[0] == [
        "porter",
        "installations",
        "list",
        "--name",
        "resource",
        "--output",
        "json",
        "--verbosity",
        "error",
    ]
    assert command.await_args_list[-1].kwargs["log_output"] is False
    outputs.assert_not_awaited()
    if expected_success is None:
        assert sender.send_messages.await_count == 1
    else:
        assert sender.send_messages.await_count == 2
        final_status = json.loads(str(sender.send_messages.call_args.args[0]))
        assert final_status["status"] == ("deleted" if expected_success else "deleting_failed")
        assert "outputs" not in final_status
        if expected_success:
            assert "Porter confirmed that the installation is absent" in final_status["message"]
        else:
            assert error in final_status["message"]


@pytest.mark.asyncio
@patch("vmss_porter.runner.run_command_helper")
async def test_run_porter_azure_login_failure(mock_run_command_helper):
    """Test run_porter function with Azure login failure."""
    config = {"azure_environment": "AzureCloud", "vmss_msi_id": "msi_id", "porter_env": {}}
    command = [["porter", "install", "test_installation"]]

    # Mock Azure login failure
    mock_run_command_helper.return_value = (1, None, "azure login error")

    returncode, stdout, stderr = await run_porter(command, config)

    assert returncode == 1
    assert stdout is None
    assert stderr == "azure login error"
    assert mock_run_command_helper.call_count == 1


@pytest.mark.asyncio
@patch("vmss_porter.runner.run_command_helper")
async def test_run_porter_acr_login_failure(mock_run_command_helper):
    """Test run_porter function with ACR login failure."""
    config = {
        "azure_environment": "AzureCloud",
        "vmss_msi_id": "msi_id",
        "registry_server": "myregistry.azurecr.io",
        "porter_env": {},
    }
    command = [["porter", "install", "test_installation"]]

    # Mock Azure login success but ACR login failure
    mock_run_command_helper.side_effect = [
        (0, "azure cloud set output", None),  # Azure cloud set succeeds
        (0, "azure login output", None),  # Azure login succeeds
        (1, None, "acr login error"),  # ACR login fails
    ]

    returncode, stdout, stderr = await run_porter(command, config)

    assert returncode == 1
    assert stdout is None
    assert stderr == "acr login error"
    assert mock_run_command_helper.call_count == 3


@pytest.mark.asyncio
@patch("vmss_porter.runner.run_command_helper")
async def test_run_porter_porter_credentials_failure(mock_run_command_helper):
    """Test run_porter function with Porter credentials failure."""
    config = {
        "azure_environment": "AzureCloud",
        "vmss_msi_id": "msi_id",
        "registry_server": "myregistry.azurecr.io",
        "porter_env": {},
    }
    command = [["porter", "install", "test_installation"]]

    # Mock Azure and ACR login success but Porter credentials failure
    mock_run_command_helper.side_effect = [
        (0, "azure cloud set output", None),  # Azure cloud set succeeds
        (0, "azure login output", None),  # Azure login succeeds
        (0, "acr login output", None),  # ACR login succeeds
        (1, None, "porter creds error"),  # Porter credential sets fails
    ]

    returncode, stdout, stderr = await run_porter(command, config)

    assert returncode == 1
    assert stdout is None
    assert stderr == "porter creds error"
    assert mock_run_command_helper.call_count == 4


@pytest.mark.asyncio
@patch("vmss_porter.runner.run_command_helper")
async def test_run_porter_command_injection_prevention(mock_run_command_helper):
    """Test that run_porter prevents command injection by using split commands."""
    config = {
        "azure_environment": "AzureCloud",
        "vmss_msi_id": "msi_id",
        "registry_server": "myregistry.azurecr.io",
        "porter_env": {},
    }

    # A command that could potentially have injection issues
    command = [["porter", "install", "installation_id", "--param", "param=value; malicious_command"]]

    # Mock successful execution of all commands
    mock_run_command_helper.side_effect = [
        (0, "azure cloud set output", None),  # Azure cloud set succeeds
        (0, "azure login output", None),  # Azure login succeeds
        (0, "acr login output", None),  # ACR login succeeds
        (0, "porter cred output 1", None),  # Porter credential set 1 succeeds
        (0, "porter cred output 2", None),  # Porter credential set 2 succeeds
        (0, "porter command output", None),  # Porter command succeeds
    ]

    await run_porter(command, config)

    # Check that each command is passed as a list to run_command_helper
    for call_args in mock_run_command_helper.call_args_list:
        assert isinstance(call_args[0][0], list)


@pytest.mark.asyncio
@patch(
    "vmss_porter.runner.build_porter_command_for_outputs", return_value=[["porter", "installations", "output", "list"]]
)
@patch(
    "vmss_porter.runner.run_porter", return_value=(0, json.dumps([{"name": "output1", "value": "value1"}]), "stderr")
)
async def test_get_porter_outputs(mock_run_porter, mock_build_porter_command_for_outputs):
    """Test getting porter outputs."""
    config = {}
    msg_body = {"id": "test_id", "action": "install"}

    success, outputs = await get_porter_outputs(msg_body, config)

    assert success is True
    assert outputs == [{"name": "output1", "value": "value1"}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "output_result, expected_status",
    [
        pytest.param(
            (1, None, "ERROR: Could not connect to the registry login server 'tre.azurecr.io'."),
            "updating_failed",
            id="output-command-fails",
        ),
        pytest.param((0, "not json", None), "updated", id="invalid-json"),
    ],
)
async def test_invoke_porter_action_sends_outputs_as_a_list(output_result, expected_status):
    # The API model reads outputs as a list. A dict fails validation, so the
    # API never records the status and the operation stays in progress.
    sender = AsyncMock()
    client = Mock()
    client.get_queue_sender.return_value = sender
    config = {"deployment_status_queue": "test_queue"}
    msg_body = {"id": "test_id", "action": "upgrade", "stepId": "test_step_id", "operationId": "test_operation_id"}

    with (
        patch("vmss_porter.runner.build_porter_command", return_value=([["porter", "upgrade"]], None, "params", None)),
        patch("vmss_porter.runner.build_porter_command_for_outputs", return_value=[["porter", "output", "list"]]),
        patch("vmss_porter.runner.run_porter", side_effect=[(0, "", None), output_result]),
    ):
        await invoke_porter_action(msg_body, client, config)

    final_status = json.loads(str(sender.send_messages.call_args.args[0]))
    assert final_status["status"] == expected_status
    assert final_status["outputs"] == []


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_check_runners(_):
    """Test checking runners."""
    mock_process = Mock()
    mock_process.is_alive.return_value = False
    processes = [mock_process]
    mock_httpserver = AsyncMock()
    mock_httpserver.kill.return_value = None

    run_once = Mock(side_effect=[True, False])

    await check_runners(processes, mock_httpserver, keep_running=run_once)
    assert mock_httpserver.kill.call_count == 1


def session_receiver(mock_service_bus_client, body):
    mock_service_bus_client_instance = mock_service_bus_client.return_value
    mock_receiver = AsyncMock()
    mock_receiver.__aenter__.return_value = mock_receiver
    mock_receiver.__aexit__.return_value = None
    mock_receiver.session.session_id = "test_id"
    mock_receiver.__aiter__.return_value = [json.dumps(body)]
    mock_service_bus_client_instance.get_queue_receiver.return_value.__aenter__.return_value = mock_receiver
    return mock_service_bus_client_instance, mock_receiver


VALID_REQUEST = {
    "id": "test_id",
    "action": "install",
    "stepId": "test_step_id",
    "operationId": "test_operation_id",
    "name": "test_bundle",
    "version": "1.0.0",
    "parameters": {},
}


@pytest.mark.asyncio
@patch("vmss_porter.runner.run_step", return_value=True)
async def test_each_step_runs_with_the_lease_for_its_resource(
    mock_run_step, mock_service_bus_client, mock_execution_lease, mock_keep_renewed
):
    client, receiver = session_receiver(mock_service_bus_client, VALID_REQUEST)
    executions = AsyncMock()

    await receive_message(
        client, {"resource_request_queue": "q"}, executions, keep_running=Mock(side_effect=[True, False])
    )

    container, resource_id, describe = mock_execution_lease.call_args.args
    assert (container, resource_id) == (executions, "test_id")
    assert describe() == "resource_id=test_id, operation_id=test_operation_id, step_id=test_step_id"
    assert mock_run_step.await_args.args[1] is mock_execution_lease.execution
    receiver.complete_message.assert_awaited_once()
    assert mock_keep_renewed.call_args.args[0] == "Session lock"


@pytest.mark.asyncio
@patch("vmss_porter.runner.run_step", return_value=True)
async def test_a_lost_session_lock_at_completion_is_a_warning(
    mock_run_step, mock_service_bus_client, mock_execution_lease, mock_keep_renewed, mock_logger
):
    client, receiver = session_receiver(mock_service_bus_client, VALID_REQUEST)
    receiver.complete_message.side_effect = SessionLockLostError()

    with patch("vmss_porter.runner.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await receive_message(
            client, {"resource_request_queue": "q"}, AsyncMock(), keep_running=Mock(side_effect=[True, False])
        )

    assert "The session lock expired before the message was completed" in mock_logger.warning.call_args.args[0]
    mock_logger.exception.assert_not_called()
    mock_sleep.assert_not_awaited()


@pytest.mark.asyncio
@patch("vmss_porter.runner.run_step", return_value=True)
async def test_a_session_lost_during_the_lease_wait_runs_no_porter(
    mock_run_step, mock_service_bus_client, mock_execution_lease, mock_keep_renewed, mock_logger
):
    # Another worker can have the message now, and a later step for the resource can have finished.
    client, receiver = session_receiver(mock_service_bus_client, VALID_REQUEST)
    receiver.session.renew_lock.side_effect = SessionLockLostError()

    await receive_message(
        client, {"resource_request_queue": "q"}, AsyncMock(), keep_running=Mock(side_effect=[True, False])
    )

    mock_run_step.assert_not_awaited()
    receiver.complete_message.assert_not_awaited()
    assert "lost its session while it waited for the lease" in mock_logger.warning.call_args.args[0]
    mock_logger.exception.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_setting, running, paused", [(False, True, False), (True, False, False), (True, True, True)]
)
async def test_the_test_setting_pauses_the_session_lock_only_while_porter_runs(
    mock_service_bus_client, mock_execution_lease, mock_keep_renewed, test_setting, running, paused
):
    client, _ = session_receiver(mock_service_bus_client, VALID_REQUEST)
    seen = []

    async def run_step(*args):
        seen.append(mock_keep_renewed.call_args.kwargs["paused"]())
        return True

    config = {"resource_request_queue": "q", "test_skip_session_lock_renewal": test_setting}
    with patch("vmss_porter.runner.run_step", side_effect=run_step):
        await receive_message(client, config, AsyncMock(), keep_running=Mock(side_effect=[True, False]))

    if running:
        assert seen == [paused]
    assert mock_keep_renewed.call_args.kwargs["paused"]() is False


def failing_lease(status_code, reason):
    error = HttpResponseError(message="storage error")
    error.status_code, error.reason = status_code, reason

    @asynccontextmanager
    async def lease(container, resource_id, describe):
        raise error
        yield

    return patch("vmss_porter.runner.execution_lease", side_effect=lease)


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code, reason", [(403, "Forbidden"), (401, "Unauthorized")])
async def test_no_access_to_the_execution_record_fails_the_step(
    mock_service_bus_client, mock_keep_renewed, status_code, reason
):
    client, receiver = session_receiver(mock_service_bus_client, VALID_REQUEST)
    client.get_queue_sender.return_value.send_messages = AsyncMock()
    config = {"resource_request_queue": "q", "deployment_status_queue": "status"}

    with failing_lease(status_code, reason), patch("vmss_porter.runner.run_step") as run_step:
        await receive_message(client, config, AsyncMock(), keep_running=Mock(side_effect=[True, False]))

    run_step.assert_not_called()
    sent = json.loads(str(client.get_queue_sender.return_value.send_messages.await_args.args[0]))
    assert sent["status"] == "deployment_failed"
    assert f"HTTP {status_code} {reason}" in sent["message"]
    assert "executionId" not in sent
    receiver.complete_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_a_short_storage_failure_leaves_the_message_for_a_redelivery(
    mock_service_bus_client, mock_keep_renewed, mock_logger
):
    client, receiver = session_receiver(mock_service_bus_client, VALID_REQUEST)
    client.get_queue_sender.return_value.send_messages = AsyncMock()

    with (
        failing_lease(503, "Server Busy"),
        patch("vmss_porter.runner.asyncio.sleep", new_callable=AsyncMock),
    ):
        await receive_message(
            client, {"resource_request_queue": "q"}, AsyncMock(), keep_running=Mock(side_effect=[True, False])
        )

    client.get_queue_sender.return_value.send_messages.assert_not_awaited()
    receiver.complete_message.assert_not_awaited()
    assert "with HTTP 503" in mock_logger.error.call_args.args[0]
