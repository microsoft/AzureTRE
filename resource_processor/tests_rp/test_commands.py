import json
import asyncio
import os
import logging
import base64
import stat
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, AsyncMock
from helpers.commands import (
    azure_login_command,
    apply_porter_credentials_sets_command,
    azure_acr_login_command,
    build_porter_command,
    build_porter_command_for_outputs,
    get_porter_parameter_keys,
    run_command_helper,
    get_special_porter_param_value,
    cleanup_parameter_value_files,
)


@pytest.fixture
def mock_get_porter_parameter_keys():
    with patch("helpers.commands.get_porter_parameter_keys", new_callable=AsyncMock) as mock:
        yield mock


@pytest.mark.parametrize(
    "config, expected_commands",
    [
        (
            {"azure_environment": "AzureCloud", "vmss_msi_id": "msi_id"},
            [["az", "cloud", "set", "--name", "AzureCloud"], ["az", "login", "--identity", "--client-id", "msi_id"]],
        ),
        (
            {
                "azure_environment": "AzureCloud",
                "arm_client_id": "client_id",
                "arm_client_secret": "client_secret",
                "arm_tenant_id": "tenant_id",
            },
            [
                ["az", "cloud", "set", "--name", "AzureCloud"],
                [
                    "az",
                    "login",
                    "--service-principal",
                    "--username",
                    "client_id",
                    "--password",
                    "client_secret",
                    "--tenant",
                    "tenant_id",
                ],
            ],
        ),
    ],
)
def test_azure_login_command(config, expected_commands):
    """Test azure_login_command function."""
    assert azure_login_command(config) == expected_commands


@pytest.mark.parametrize(
    "config, expected_commands",
    [
        (
            {"vmss_msi_id": "msi_id"},
            [
                ["porter", "credentials", "apply", "vmss_porter/arm_auth_local_debugging.json"],
                ["porter", "credentials", "apply", "vmss_porter/aad_auth.json"],
            ],
        ),
        (
            {},
            [
                ["porter", "credentials", "apply", "vmss_porter/arm_auth_local_debugging.json"],
                ["porter", "credentials", "apply", "vmss_porter/aad_auth_local_debugging.json"],
            ],
        ),
    ],
)
def test_apply_porter_credentials_sets_command(config, expected_commands):
    """Test apply_porter_credentials_sets_command function."""
    assert apply_porter_credentials_sets_command(config) == expected_commands


@pytest.mark.parametrize(
    "config, expected_commands",
    [({"registry_server": "myregistry.azurecr.io"}, [["az", "acr", "login", "--name", "myregistry"]])],
)
def test_azure_acr_login_command(config, expected_commands):
    """Test azure_acr_login_command function."""
    assert azure_acr_login_command(config) == expected_commands


@pytest.mark.asyncio
async def test_build_porter_command(mock_get_porter_parameter_keys):
    """Test build_porter_command function."""
    config = {"registry_server": "myregistry.azurecr.io"}
    msg_body = {
        "id": "guid",
        "action": "install",
        "name": "mybundle",
        "version": "1.0.0",
        "parameters": {"param1": "value1"},
    }
    mock_get_porter_parameter_keys.return_value = ["param1"]

    commands, param_set_file, param_set_name, installation_file = await build_porter_command(config, msg_body)
    try:
        assert param_set_file is not None
        assert param_set_name.startswith("tre-params-guid-")
        assert len(param_set_name) == len("tre-params-guid-") + 8
        assert os.path.exists(param_set_file)
        assert installation_file is not None
        assert os.path.exists(installation_file)

        # First command applies the parameter set to Porter's store
        assert commands[0] == ["porter", "parameters", "apply", param_set_file]

        # Second command is porter installation apply using the installation file
        assert commands[1] == [
            "porter",
            "installation",
            "apply",
            installation_file,
            "--force",
            "--verbosity",
            "warning",
        ]

        with open(param_set_file) as f:
            param_set = json.load(f)

        assert param_set["schemaType"] == "ParameterSet"
        assert param_set["name"] == param_set_name
        assert len(param_set["parameters"]) == 1
        assert param_set["parameters"][0]["name"] == "param1"
        assert set(param_set["parameters"][0]["source"]) == {"path"}
        assert Path(param_set["parameters"][0]["source"]["path"]).read_text() == "value1"
        assert "value1" not in Path(param_set_file).read_text()

        with open(installation_file) as f:
            installation = json.load(f)

        assert installation["schemaType"] == "Installation"
        assert installation["name"] == "guid"
        assert installation["parameters"] == {}
        assert installation["parameterSets"] == [param_set_name]
        assert installation["credentialSets"] == ["arm_auth", "aad_auth"]
        assert installation["bundle"]["repository"] == "myregistry.azurecr.io/mybundle"
        assert installation["bundle"]["version"] == "1.0.0"
    finally:
        if param_set_file and os.path.exists(param_set_file):
            cleanup_parameter_value_files(param_set_file)
            os.unlink(param_set_file)
        if installation_file and os.path.exists(installation_file):
            os.unlink(installation_file)


@pytest.mark.asyncio
async def test_build_porter_command_for_upgrade(mock_get_porter_parameter_keys):
    """Test build_porter_command function for upgrade action."""
    config = {"registry_server": "myregistry.azurecr.io"}
    msg_body = {
        "id": "guid",
        "action": "upgrade",
        "name": "mybundle",
        "version": "1.0.0",
        "parameters": {"param1": "value1"},
    }
    mock_get_porter_parameter_keys.return_value = ["param1"]

    commands, param_set_file, param_set_name, installation_file = await build_porter_command(config, msg_body)
    try:
        assert param_set_file is not None
        assert param_set_name.startswith("tre-params-guid-")
        assert os.path.exists(param_set_file)
        assert installation_file is not None
        assert os.path.exists(installation_file)

        # First command applies the parameter set to Porter's store
        assert commands[0] == ["porter", "parameters", "apply", param_set_file]

        # Second command is porter installation apply (not porter upgrade)
        assert commands[1] == [
            "porter",
            "installation",
            "apply",
            installation_file,
            "--force",
            "--verbosity",
            "warning",
        ]

        with open(installation_file) as f:
            installation = json.load(f)

        assert installation["parameters"] == {}
        assert installation["parameterSets"] == [param_set_name]
    finally:
        if param_set_file and os.path.exists(param_set_file):
            cleanup_parameter_value_files(param_set_file)
            os.unlink(param_set_file)
        if installation_file and os.path.exists(installation_file):
            os.unlink(installation_file)


@pytest.mark.asyncio
async def test_build_porter_command_for_outputs():
    """Test build_porter_command_for_outputs function."""
    msg_body = {"id": "guid", "action": "install", "name": "mybundle", "version": "1.0.0"}
    expected_command = [["porter", "installations", "output", "list", "--installation", "guid", "--output", "json"]]

    command = await build_porter_command_for_outputs(msg_body)
    assert command == expected_command


@pytest.mark.asyncio
async def test_build_porter_command_no_parameters(mock_get_porter_parameter_keys):
    """Test build_porter_command with no parameters: no param set file, but installation file with empty parameterSets."""
    config = {"registry_server": "myregistry.azurecr.io"}
    msg_body = {"id": "guid", "action": "install", "name": "mybundle", "version": "1.0.0", "parameters": {}}
    mock_get_porter_parameter_keys.return_value = []

    commands, param_set_file, param_set_name, installation_file = await build_porter_command(config, msg_body)

    try:
        assert param_set_file is None
        assert param_set_name.startswith("tre-params-guid-")
        assert installation_file is not None
        assert os.path.exists(installation_file)

        assert commands == [["porter", "installation", "apply", installation_file, "--force", "--verbosity", "warning"]]

        with open(installation_file) as f:
            installation = json.load(f)

        assert installation["parameters"] == {}
        assert installation["parameterSets"] == []
        assert installation["credentialSets"] == ["arm_auth", "aad_auth"]
    finally:
        if installation_file and os.path.exists(installation_file):
            os.unlink(installation_file)


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
        "parameters": {"dict_param": dict_value, "list_param": list_value, "string_param": "simple_value"},
    }

    mock_get_porter_parameter_keys.return_value = ["dict_param", "list_param", "string_param"]

    commands, param_set_file, param_set_name, installation_file = await build_porter_command(config, msg_body)

    try:
        # First command is the apply command
        assert commands[0] == ["porter", "parameters", "apply", param_set_file]

        # Second command is porter installation apply
        assert commands[1] == [
            "porter",
            "installation",
            "apply",
            installation_file,
            "--force",
            "--verbosity",
            "warning",
        ]

        assert param_set_name.startswith("tre-params-guid-")

        # Verify the param set file contains the correct parameters
        assert param_set_file is not None
        with open(param_set_file) as f:
            param_set = json.load(f)

        params_by_name = {p["name"]: Path(p["source"]["path"]).read_text() for p in param_set["parameters"]}

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

        # Verify the installation file references the parameter set
        assert installation_file is not None
        with open(installation_file) as f:
            installation = json.load(f)

        assert installation["parameters"] == {}
        assert installation["parameterSets"] == [param_set_name]
    finally:
        if param_set_file and os.path.exists(param_set_file):
            cleanup_parameter_value_files(param_set_file)
            os.unlink(param_set_file)
        if installation_file and os.path.exists(installation_file):
            os.unlink(installation_file)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action, custom_action", [("install", False), ("upgrade", False), ("uninstall", False), ("start", True)]
)
async def test_build_porter_command_large_firewall_parameters(
    mock_get_porter_parameter_keys, tmp_path, monkeypatch, action, custom_action
):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    parameters = {
        name: [
            {
                "name": f"workspace-{index}",
                "priority": 1000 + index,
                "rules": [{"name": f"rule-{rule}", "destination": f"service-{rule}.example.com"} for rule in range(20)],
            }
            for index in range(200)
        ]
        for name in ("rule_collections", "network_rule_collections")
    }
    mock_get_porter_parameter_keys.return_value = list(parameters)
    msg_body = {"id": "guid", "action": action, "name": "mybundle", "version": "1.0.0", "parameters": parameters}

    commands, param_set_file, param_set_name, installation_file = await build_porter_command(
        {"registry_server": "myregistry.azurecr.io"}, msg_body, custom_action
    )

    assert all("--param" not in command for command in commands)
    assert sum(len(arg.encode()) + 1 for command in commands for arg in command) < 4096
    assert commands[0] == ["porter", "parameters", "apply", param_set_file]
    with open(param_set_file) as f:
        parameter_set = json.load(f)
    assert parameter_set["schemaType"] == "ParameterSet"
    assert parameter_set["name"] == param_set_name
    assert len(parameter_set["parameters"]) == 2
    for parameter in parameter_set["parameters"]:
        assert set(parameter["source"]) == {"path"}
        value = Path(parameter["source"]["path"]).read_text()
        assert len(value) > 128 * 1024
        assert json.loads(base64.b64decode(value)) == parameters[parameter["name"]]

    if installation_file:
        with open(installation_file) as f:
            assert json.load(f)["parameterSets"] == [param_set_name]
    else:
        assert commands[1][commands[1].index("--parameter-set") + 1] == param_set_name

    for path in tmp_path.rglob("*"):
        assert stat.S_IMODE(path.stat().st_mode) == (0o700 if path.is_dir() else 0o600)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure_stage",
    ["parameter_write", "value_create", "value_write", "installation_create", "installation_write", "command_build"],
)
async def test_build_porter_command_removes_files_on_failure(
    mock_get_porter_parameter_keys, tmp_path, monkeypatch, failure_stage
):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    mock_get_porter_parameter_keys.return_value = ["param1"]
    msg_body = {
        "id": "guid",
        "action": "install",
        "name": "mybundle",
        "version": "1.0.0",
        "parameters": {"param1": "secret"},
    }
    config = {"registry_server": "myregistry.azurecr.io"}
    original_dump = json.dump
    original_tempfile = tempfile.NamedTemporaryFile

    def dump(document, stream):
        should_fail = (failure_stage == "parameter_write" and document["schemaType"] == "ParameterSet") or (
            failure_stage == "installation_write" and document["schemaType"] == "Installation"
        )
        if should_fail:
            stream.write("partial secret document")
            raise OSError("document write failed")
        return original_dump(document, stream)

    def create_file(*args, **kwargs):
        if failure_stage == "value_create" and kwargs.get("dir"):
            raise OSError("value creation failed")
        if failure_stage == "installation_create" and not kwargs.get("dir") and list(tmp_path.iterdir()):
            raise OSError("document creation failed")
        stream = original_tempfile(*args, **kwargs)
        if failure_stage == "value_write" and kwargs.get("dir"):
            original_write = stream.write

            def fail_write(value):
                original_write(value[:3])
                raise OSError("value write failed")

            stream.write = fail_write
        return stream

    monkeypatch.setattr("helpers.commands.json.dump", dump)
    monkeypatch.setattr("helpers.commands.tempfile.NamedTemporaryFile", create_file)
    if failure_stage == "command_build":
        msg_body["action"] = "start"
        del config["registry_server"]

    with pytest.raises((OSError, KeyError)):
        await build_porter_command(config, msg_body, custom_action=failure_stage == "command_build")

    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_build_porter_command_custom_action(mock_get_porter_parameter_keys):
    """Test that custom actions use porter invoke --action (regression guard)."""
    config = {"registry_server": "myregistry.azurecr.io"}
    msg_body = {
        "id": "guid",
        "action": "start",
        "name": "mybundle",
        "version": "1.0.0",
        "parameters": {"param1": "value1"},
    }
    mock_get_porter_parameter_keys.return_value = ["param1"]

    commands, param_set_file, param_set_name, installation_file = await build_porter_command(
        config, msg_body, custom_action=True
    )
    try:
        assert installation_file is None

        # First command applies the parameter set
        assert commands[0] == ["porter", "parameters", "apply", param_set_file]

        # Second command uses porter invoke --action (not installation apply)
        assert commands[1] == [
            "porter",
            "invoke",
            "--action",
            "start",
            "guid",
            "--reference",
            "myregistry.azurecr.io/mybundle:v1.0.0",
            "--parameter-set",
            param_set_name,
            "--force",
            "--credential-set",
            "arm_auth",
            "--credential-set",
            "aad_auth",
        ]
    finally:
        if param_set_file and os.path.exists(param_set_file):
            cleanup_parameter_value_files(param_set_file)
            os.unlink(param_set_file)


@pytest.mark.asyncio
@patch("helpers.commands.run_command_helper")
async def test_get_porter_parameter_keys(mock_run_command_helper):
    """Test get_porter_parameter_keys function."""
    config = {
        "registry_server": "myregistry.azurecr.io",
        "azure_environment": "AzureCloud",
        "porter_env": {},
        "arm_client_id": "client_id",
        "arm_client_secret": "client_secret",
        "arm_tenant_id": "tenant_id",
    }
    msg_body = {"name": "mybundle", "version": "1.0.0"}

    porter_explain_output = json.dumps({"parameters": [{"name": "param1"}]})

    # Need to account for multiple commands per operation (cloud set, login, etc)
    mock_run_command_helper.side_effect = [
        (0, "cloud set output", None),  # az cloud set
        (0, "login output", None),  # az login
        (0, "acr login output", None),  # az acr login
        (0, porter_explain_output, None),  # porter explain
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
    expected_reference = "{}/{}:v{}".format(config["registry_server"], msg_body["name"], msg_body["version"])
    assert expected_reference == command_args[3]


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
            "echo",
            "test",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=config["porter_env"],
            start_new_session=True,
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
@patch("helpers.commands.shell_output_logger")
async def test_run_command_helper_error_best_effort_logs_debug(mock_shell_output_logger):
    """Best-effort failures should reduce stderr logging severity to debug."""
    config = {"porter_env": {}}
    cmd_parts = ["command_that_fails"]

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"error output")
        mock_proc.returncode = 1
        mock_subprocess.return_value = mock_proc

        returncode, stdout, stderr = await run_command_helper(cmd_parts, config, "Best-effort command", log_error=False)

        assert returncode == 1
        assert stdout is None
        assert stderr == "error output"
        mock_shell_output_logger.assert_called_once_with("error output", "[stderr]", logging.DEBUG)


@pytest.mark.asyncio
@patch("helpers.commands.shell_output_logger")
async def test_run_command_helper_can_capture_sensitive_output_without_logging(mock_shell_output_logger):
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b'{"secret": "stored-value"}', b"sensitive diagnostic")
        mock_proc.returncode = 0
        mock_subprocess.return_value = mock_proc

        result = await run_command_helper(["porter", "show"], {"porter_env": {}}, "Read installation", log_output=False)

    assert result == (0, '{"secret": "stored-value"}', "sensitive diagnostic")
    mock_shell_output_logger.assert_not_called()


@pytest.mark.asyncio
@patch("helpers.commands.run_command_helper")
async def test_get_porter_parameter_keys_command_splitting(mock_run_command_helper):
    """Test that commands are properly split for security in get_porter_parameter_keys."""
    config = {
        "registry_server": "myregistry.azurecr.io",
        "azure_environment": "AzureCloud",
        "porter_env": {},
        "vmss_msi_id": "msi_id",
    }
    msg_body = {"name": "mybundle", "version": "1.0.0"}

    porter_explain_output = json.dumps({"parameters": [{"name": "param1"}]})

    # We need more side effects now since there are multiple commands per step
    mock_run_command_helper.side_effect = [
        (0, "cloud set output", None),  # First az cloud set
        (0, "login output", None),  # Then az login
        (0, "acr login output", None),  # Then az acr login
        (0, porter_explain_output, None),  # Finally porter explain
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
        "bundle_params": {"custom_param": "custom_value"},
    }

    msg_body = {"workspaceId": "ws-123", "parentWorkspaceServiceId": "parent-123", "ownerId": "owner-123"}

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
