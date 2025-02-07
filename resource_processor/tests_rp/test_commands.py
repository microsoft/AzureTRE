import json
import pytest
from unittest.mock import patch, AsyncMock
from helpers.commands import azure_login_command, apply_porter_credentials_sets_command, azure_acr_login_command, build_porter_command, build_porter_command_for_outputs, get_porter_parameter_keys

@pytest.fixture
def mock_get_porter_parameter_keys():
    with patch("helpers.commands.get_porter_parameter_keys", new_callable=AsyncMock) as mock:
        yield mock

@pytest.mark.parametrize("config, expected_command", [
    ({"azure_environment": "AzureCloud", "vmss_msi_id": "msi_id"}, "az cloud set --name AzureCloud >/dev/null  && az login --identity -u msi_id >/dev/null "),
    ({"azure_environment": "AzureCloud", "arm_client_id": "client_id", "arm_client_secret": "client_secret", "arm_tenant_id": "tenant_id"}, "az cloud set --name AzureCloud >/dev/null  && az login --service-principal --username client_id --password client_secret --tenant tenant_id >/dev/null")
])
def test_azure_login_command(config, expected_command):
    """Test azure_login_command function."""
    assert azure_login_command(config) == expected_command

@pytest.mark.parametrize("config, expected_command", [
    ({"vmss_msi_id": "msi_id"}, "porter credentials apply vmss_porter/arm_auth_local_debugging.json >/dev/null 2>&1 && porter credentials apply vmss_porter/aad_auth.json >/dev/null 2>&1"),
    ({}, "porter credentials apply vmss_porter/arm_auth_local_debugging.json >/dev/null 2>&1 && porter credentials apply vmss_porter/aad_auth_local_debugging.json >/dev/null 2>&1")
])
def test_apply_porter_credentials_sets_command(config, expected_command):
    """Test apply_porter_credentials_sets_command function."""
    assert apply_porter_credentials_sets_command(config) == expected_command

@pytest.mark.parametrize("config, expected_command", [
    ({"registry_server": "myregistry.azurecr.io"}, "az acr login --name myregistry >/dev/null ")
])
def test_azure_acr_login_command(config, expected_command):
    """Test azure_acr_login_command function."""
    assert azure_acr_login_command(config) == expected_command

@pytest.mark.asyncio
async def test_build_porter_command(mock_get_porter_parameter_keys):
    """Test build_porter_command function."""
    config = {"registry_server": "myregistry.azurecr.io"}
    msg_body = {"id": "guid", "action": "install", "name": "mybundle", "version": "1.0.0", "parameters": {"param1": "value1"}}
    mock_get_porter_parameter_keys.return_value = ["param1"]

    expected_command = [
        "porter install \"guid\" --reference myregistry.azurecr.io/mybundle:v1.0.0 --param param1=\"value1\" --force --credential-set arm_auth --credential-set aad_auth"
    ]

    command = await build_porter_command(config, msg_body)
    assert command == expected_command

@pytest.mark.asyncio
async def test_build_porter_command_for_upgrade(mock_get_porter_parameter_keys):
    """Test build_porter_command function for upgrade action."""
    config = {"registry_server": "myregistry.azurecr.io"}
    msg_body = {"id": "guid", "action": "upgrade", "name": "mybundle", "version": "1.0.0", "parameters": {"param1": "value1"}}
    mock_get_porter_parameter_keys.return_value = ["param1"]

    expected_command = [
        "porter upgrade \"guid\" --reference myregistry.azurecr.io/mybundle:v1.0.0 --param param1=\"value1\" --force --credential-set arm_auth --credential-set aad_auth --force-upgrade"
    ]

    command = await build_porter_command(config, msg_body)
    assert command == expected_command

@pytest.mark.asyncio
async def test_build_porter_command_for_outputs():
    """Test build_porter_command_for_outputs function."""
    msg_body = {"id": "guid", "action": "install", "name": "mybundle", "version": "1.0.0"}
    expected_command = ["porter installations output list --installation guid --output json"]

    command = await build_porter_command_for_outputs(msg_body)
    assert command == expected_command

@pytest.mark.asyncio
@patch("helpers.commands.azure_login_command", return_value="az login command")
@patch("helpers.commands.azure_acr_login_command", return_value="az acr login command")
@patch("asyncio.create_subprocess_shell")
async def test_get_porter_parameter_keys(mock_create_subprocess_shell, mock_azure_acr_login_command, mock_azure_login_command):
    """Test get_porter_parameter_keys function."""
    config = {"registry_server": "myregistry.azurecr.io", "porter_env": {}}
    msg_body = {"name": "mybundle", "version": "1.0.0"}
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (json.dumps({"parameters": [{"name": "param1"}]}).encode(), b"")
    mock_create_subprocess_shell.return_value = mock_proc

    expected_keys = ["param1"]

    keys = await get_porter_parameter_keys(config, msg_body)
    assert keys == expected_keys
