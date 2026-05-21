import json
import asyncio
import os
import pytest
from unittest.mock import patch, AsyncMock
from helpers.commands import azure_login_command, apply_porter_credentials_sets_command, azure_acr_login_command, build_porter_command, build_porter_command_for_outputs, get_porter_parameter_keys, run_command_helper, get_special_porter_param_value


@pytest.fixture
def mock_get_porter_parameter_keys():
    with patch("helpers.commands.get_porter_parameter_keys", new_callable=AsyncMock) as mock:
        yield mock


@pytest.mark.parametrize("config, expected_commands", [
    ({"azure_environment": "AzureCloud", "vmss_msi_id": "msi_id"}, [
        ["az", "cloud", "set", "--name", "AzureCloud"],
        ["az", "login", "--identity", "--client-id", "msi_id"]
    ]),
    ({"azure_environment": "AzureCloud", "arm_client_id": "client_id", "arm_client_secret": "client_secret", "arm_tenant_id": "tenant_id"}, [
        ["az", "cloud", "set", "--name", "AzureCloud"],
        ["az", "login", "--service-principal", "--username", "client_id", "--password", "client_secret", "--tenant", "tenant_id"]
    ])
])
def test_azure_login_command(config, expected_commands):
    """Test azure_login_command function."""
    assert azure_login_command(config) == expected_commands


@pytest.mark.parametrize("config, expected_commands", [
    ({"vmss_msi_id": "msi_id"}, [
        ["porter", "credentials", "apply", "vmss_porter/arm_auth_local_debugging.json"],
        ["porter", "credentials", "apply", "vmss_porter/aad_auth.json"]
    ]),
    ({}, [
        ["porter", "credentials", "apply", "vmss_porter/arm_auth_local_debugging.json"],
        ["porter", "credentials", "apply", "vmss_porter/aad_auth_local_debugging.json"]
    ])
])
def test_apply_porter_credentials_sets_command(config, expected_commands):
    """Test apply_porter_credentials_sets_command function."""
    assert apply_porter_credentials_sets_command(config) == expected_commands


@pytest.mark.parametrize("config, expected_commands", [
    ({"registry_server": "myregistry.azurecr.io"}, [
        ["az", "acr", "login", "--name", "myregistry"]
    ])
])
def test_azure_acr_login_command(config, expected_commands):
    """Test azure_acr_login_command function."""
    assert azure_acr_login_command(config) == expected_commands


@pytest.mark.asyncio
async def test_build_porter_command(mock_get_porter_parameter_keys):
    """Test build_porter_command function."""
    config = {"registry_server": "myregistry.azurecr.io"}
    msg_body = {"id": "guid", "action": "install", "name": "mybundle", "version": "1.0.0", "parameters": {"param1": "value1"}}
    mock_get_porter_parameter_keys.return_value = ["param1"]

    commands, param_set_file, param_set_name = await build_porter_command(config, msg_body)
    try:
        assert param_set_file is not None
        assert param_set_name.startswith("tre-params-guid-")
        assert len(param_set_name) == len("tre-params-guid-") + 8
        assert os.path.exists(param_set_file)

        # First command applies the parameter set to Porter's store
        assert commands[0] == ["porter", "parameters", "apply", param_set_file]

        # Second command is the main porter install using the parameter set by name
        assert commands[1] == [
            "porter", "install", "guid",
            "--reference", "myregistry.azurecr.io/mybundle:v1.0.0",
            "--parameter-set", param_set_name,
            "--force",
            "--credential-set", "arm_auth",
            "--credential-set", "aad_auth"
        ]

        with open(param_set_file) as f:
            param_set = json.load(f)

        assert param_set["schemaType"] == "ParameterSet"
        assert param_set["name"] == param_set_name
        assert len(param_set["parameters"]) == 1
        assert param_set["parameters"][0] == {"name": "param1", "source": {"value": "value1"}}
    finally:
        if param_set_file and os.path.exists(param_set_file):
            os.unlink(param_set_file)


@pytest.mark.asyncio
async def test_build_porter_command_for_upgrade(mock_get_porter_parameter_keys):
    """Test build_porter_command function for upgrade action."""
    config = {"registry_server": "myregistry.azurecr.io"}
    msg_body = {"id": "guid", "action": "upgrade", "name": "mybundle", "version": "1.0.0", "parameters": {"param1": "value1"}}
    mock_get_porter_parameter_keys.return_value = ["param1"]

    commands, param_set_file, param_set_name = await build_porter_command(config, msg_body)
    try:
        assert param_set_file is not None
        assert param_set_name.startswith("tre-params-guid-")
        assert os.path.exists(param_set_file)

        # First command applies the parameter set to Porter's store
        assert commands[0] == ["porter", "parameters", "apply", param_set_file]

        # Second command is the main porter upgrade using the parameter set by name
        assert commands[1] == [
            "porter", "upgrade", "guid",
            "--reference", "myregistry.azurecr.io/mybundle:v1.0.0",
            "--parameter-set", param_set_name,
            "--force",
            "--credential-set", "arm_auth",
            "--credential-set", "aad_auth",
            "--force-upgrade"
        ]
    finally:
        if param_set_file and os.path.exists(param_set_file):
            os.unlink(param_set_file)


@pytest.mark.asyncio
async def test_build_porter_command_for_outputs():
    """Test build_porter_command_for_outputs function."""
    msg_body = {"id": "guid", "action": "install", "name": "mybundle", "version": "1.0.0"}
    expected_command = [[
        "porter", "installations", "output", "list",
        "--installation", "guid",
        "--output", "json"
    ]]

    command = await build_porter_command_for_outputs(msg_body)
    assert command == expected_command


@pytest.mark.asyncio
async def test_build_porter_command_no_parameters(mock_get_porter_parameter_keys):
    """Test build_porter_command returns no --parameter-set when there are no parameters."""
    config = {"registry_server": "myregistry.azurecr.io"}
    msg_body = {"id": "guid", "action": "install", "name": "mybundle", "version": "1.0.0", "parameters": {}}
    mock_get_porter_parameter_keys.return_value = []

    commands, param_set_file, param_set_name = await build_porter_command(config, msg_body)

    assert param_set_file is None
    assert param_set_name.startswith("tre-params-guid-")
    assert commands == [[
        "porter", "install", "guid",
        "--reference", "myregistry.azurecr.io/mybundle:v1.0.0",
        "--force",
        "--credential-set", "arm_auth",
        "--credential-set", "aad_auth"
    ]]


@pytest.mark.asyncio
async def test_build_porter_command_with_complex_parameters(mock_get_porter_parameter_keys):
    """Test build_porter_command function with complex parameter types (dict, list)."""
    config = {"registry_server": "myregistry.azurecr.io"}
    dict_value = {"key1": "value1", "key2": "value2"}
    list_value = ["item1", "item2"]

    msg_body = {
        "id": "guid",
        "action": "install",
        "name": "mybundle",
        "version": "1.0.0",
        "parameters": {
            "dict_param": dict_value,
            "list_param": list_value,
            "string_param": "simple_value"
        }
    }

    mock_get_porter_parameter_keys.return_value = ["dict_param", "list_param", "string_param"]

    commands, param_set_file, param_set_name = await build_porter_command(config, msg_body)

    try:
        # First command is the apply command
        assert commands[0] == ["porter", "parameters", "apply", param_set_file]

        # Main porter command should reference the parameter set by name
        main_command = commands[1]
        assert "--parameter-set" in main_command
        assert param_set_name in main_command
        assert param_set_name.startswith("tre-params-guid-")
        assert "--param" not in main_command

        # Verify the param set file contains the correct parameters
        assert param_set_file is not None
        with open(param_set_file) as f:
            param_set = json.load(f)

        params_by_name = {p["name"]: p["source"]["value"] for p in param_set["parameters"]}

        assert "dict_param" in params_by_name
        assert "list_param" in params_by_name
        assert "string_param" in params_by_name
        assert params_by_name["string_param"] == "simple_value"

        # Verify the dict and list are base64 encoded
        import base64

        dict_encoded = base64.b64encode(json.dumps(dict_value).encode("ascii")).decode("ascii")
        list_encoded = base64.b64encode(json.dumps(list_value).encode("ascii")).decode("ascii")

        assert params_by_name["dict_param"] == dict_encoded
        assert params_by_name["list_param"] == list_encoded
    finally:
        if param_set_file and os.path.exists(param_set_file):
            os.unlink(param_set_file)


@pytest.mark.asyncio
@patch("helpers.commands.run_command_helper")
async def test_get_porter_parameter_keys(mock_run_command_helper):
    """Test get_porter_parameter_keys function."""
    config = {"registry_server": "myregistry.azurecr.io", "azure_environment": "AzureCloud", "porter_env": {}, "arm_client_id": "client_id", "arm_client_secret": "client_secret", "arm_tenant_id": "tenant_id"}
    msg_body = {"name": "mybundle", "version": "1.0.0"}

    porter_explain_output = json.dumps({"parameters": [{"name": "param1"}]})

    # Need to account for multiple commands per operation (cloud set, login, etc)
    mock_run_command_helper.side_effect = [
        (0, "cloud set output", None),   # az cloud set
        (0, "login output", None),      # az login
        (0, "acr login output", None),  # az acr login
        (0, porter_explain_output, None)  # porter explain
    ]

    expected_keys = ["param1"]
    keys = await get_porter_parameter_keys(config, msg_body)
    # Get the last call for porter explain
    call_args = mock_run_command_helper.call_args_list[-1][0]
    command_args = call_args[0]

    assert keys == expected_keys
    assert mock_run_command_helper.call_count >= 3  # At least 3 calls
    assert command_args[0] == "porter"
    assert command_args[1] == "explain"
    assert "--reference" in command_args
    assert f"{config['registry_server']}/{msg_body['name']}:v{msg_body['version']}" == command_args[3]


@pytest.mark.asyncio
async def test_run_command_helper():
    """Test the run_command_helper function with successful command execution."""
    config = {"porter_env": {}}
    cmd_parts = ["echo", "test"]

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"stdout output", b"stderr output")
        mock_proc.returncode = 0
        mock_subprocess.return_value = mock_proc

        returncode, stdout, stderr = await run_command_helper(cmd_parts, config, "Echo test")

        assert returncode == 0
        assert stdout == "stdout output"
        assert stderr == "stderr output"
        mock_subprocess.assert_called_once_with(
            "echo", "test",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=config["porter_env"]
        )


@pytest.mark.asyncio
async def test_run_command_helper_error():
    """Test the run_command_helper function with failed command execution."""
    config = {"porter_env": {}}
    cmd_parts = ["command_that_fails"]

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"error output")
        mock_proc.returncode = 1
        mock_subprocess.return_value = mock_proc

        returncode, stdout, stderr = await run_command_helper(cmd_parts, config, "Failed command")

        assert returncode == 1
        assert stdout is None
        assert stderr == "error output"


@pytest.mark.asyncio
@patch("helpers.commands.run_command_helper")
async def test_get_porter_parameter_keys_command_splitting(mock_run_command_helper):
    """Test that commands are properly split for security in get_porter_parameter_keys."""
    config = {
        "registry_server": "myregistry.azurecr.io",
        "azure_environment": "AzureCloud",
        "porter_env": {},
        "vmss_msi_id": "msi_id"
    }
    msg_body = {"name": "mybundle", "version": "1.0.0"}

    porter_explain_output = json.dumps({"parameters": [{"name": "param1"}]})

    # We need more side effects now since there are multiple commands per step
    mock_run_command_helper.side_effect = [
        (0, "cloud set output", None),   # First az cloud set
        (0, "login output", None),      # Then az login
        (0, "acr login output", None),  # Then az acr login
        (0, porter_explain_output, None)  # Finally porter explain
    ]

    await get_porter_parameter_keys(config, msg_body)

    assert mock_run_command_helper.call_count == 4

    # Verify the az cloud set command is properly split
    first_call_args = mock_run_command_helper.call_args_list[0][0]
    assert isinstance(first_call_args[0], list)
    assert first_call_args[0][0] == "az"
    assert first_call_args[0][1] == "cloud"
    assert first_call_args[0][2] == "set"

    # Verify the az login command is properly split
    second_call_args = mock_run_command_helper.call_args_list[1][0]
    assert isinstance(second_call_args[0], list)
    assert second_call_args[0][0] == "az"
    assert second_call_args[0][1] == "login"

    # Verify the acr login command is properly split
    third_call_args = mock_run_command_helper.call_args_list[2][0]
    assert isinstance(third_call_args[0], list)
    assert third_call_args[0][0] == "az"
    assert third_call_args[0][1] == "acr"
    assert third_call_args[0][2] == "login"

    # Verify the porter explain command is properly split
    fourth_call_args = mock_run_command_helper.call_args_list[3][0]
    assert isinstance(fourth_call_args[0], list)
    assert fourth_call_args[0][0] == "porter"
    assert fourth_call_args[0][1] == "explain"


def test_get_special_porter_param_value():
    """Test get_special_porter_param_value function for various special parameters."""
    config = {
        "registry_server": "myregistry.azurecr.io",
        "tfstate_resource_group_name": "tfstate-rg",
        "azure_environment": "AzureCloud",
        "aad_authority_url": "https://login.microsoftonline.com",
        "microsoft_graph_fqdn": "https://graph.microsoft.com",
        "arm_environment": "AzurePublicCloud",
        "bundle_params": {"custom_param": "custom_value"}
    }

    msg_body = {
        "workspaceId": "ws-123",
        "parentWorkspaceServiceId": "parent-123",
        "ownerId": "owner-123"
    }

    # Test ACR name extraction
    assert get_special_porter_param_value(config, "mgmt_acr_name", msg_body) == "myregistry"

    # Test resource group name
    assert get_special_porter_param_value(config, "mgmt_resource_group_name", msg_body) == "tfstate-rg"

    # Test azure environment
    assert get_special_porter_param_value(config, "azure_environment", msg_body) == "AzureCloud"

    # Test workspace ID
    assert get_special_porter_param_value(config, "workspace_id", msg_body) == "ws-123"

    # Test parent service ID
    assert get_special_porter_param_value(config, "parent_service_id", msg_body) == "parent-123"

    # Test owner ID
    assert get_special_porter_param_value(config, "owner_id", msg_body) == "owner-123"

    # Test bundle params
    assert get_special_porter_param_value(config, "custom_param", msg_body) == "custom_value"

    # Test AAD authority URL
    assert get_special_porter_param_value(config, "aad_authority_url", msg_body) == "https://login.microsoftonline.com"

    # Test Microsoft Graph FQDN (should return only the domain part)
    assert get_special_porter_param_value(config, "microsoft_graph_fqdn", msg_body) == "graph.microsoft.com"

    # Test ARM environment
    assert get_special_porter_param_value(config, "arm_environment", msg_body) == "AzurePublicCloud"

    # Test non-existent parameter
    assert get_special_porter_param_value(config, "non_existent", msg_body) is None
