import pytest
from mock import patch
from resources.commands import build_porter_command

pytestmark = pytest.mark.asyncio


@pytest.fixture
def payload():
    return {
        "operationId": "op123",
        "stepId": "step123",
        "action": "some_action",
        "user": {
            "id": "user123",
            "name": "John Doe",
            "email": "john.doe@example.com",
            "username": "johndoe",
        },
        "id": "resource123",
        "name": "Resource Name",
        "version": "1.0",
        "parameters": {
            "param1": {"key": "value"},
            "param2": ["item1", "item2"]
        }
    }


@pytest.fixture
def config():
    return {
        "registry_server": "myregistry.azurecr.io",
        "porter_env": {},
        "bundle_params": {}
    }


@patch('resources.commands.get_porter_parameter_keys')
async def test_build_porter_command_custom_action(mock_get_porter_parameter_keys, payload, config):
    mock_get_porter_parameter_keys.return_value = ["param1", "param2"]

    msg_body = payload
    msg_body["action"] = "custom_action"

    command = await build_porter_command(config, msg_body, custom_action=True)

    expected_command = [
        'porter invoke --action custom_action "resource123" --reference myregistry.azurecr.io/Resource Name:v1.0 --param param1="eyJrZXkiOiAidmFsdWUifQ==" --param param2="WyJpdGVtMSIsICJpdGVtMiJd" --force --credential-set arm_auth --credential-set aad_auth'
    ]

    assert command == expected_command


@patch('resources.commands.get_porter_parameter_keys')
async def test_build_porter_command_no_parameters(mock_get_porter_parameter_keys, payload, config):
    mock_get_porter_parameter_keys.return_value = None

    msg_body = payload

    command = await build_porter_command(config, msg_body)

    expected_command = [
        'porter some_action "resource123" --reference myregistry.azurecr.io/Resource Name:v1.0 --force --credential-set arm_auth --credential-set aad_auth'
    ]

    assert command == expected_command


@patch('resources.commands.get_porter_parameter_keys')
async def test_build_porter_command_complex_parameters(mock_get_porter_parameter_keys, payload, config):
    mock_get_porter_parameter_keys.return_value = ["param1", "param2"]

    msg_body = payload

    command = await build_porter_command(config, msg_body)

    expected_command = [
        'porter some_action "resource123" --reference myregistry.azurecr.io/Resource Name:v1.0 --param param1="eyJrZXkiOiAidmFsdWUifQ==" --param param2="WyJpdGVtMSIsICJpdGVtMiJd" --force --credential-set arm_auth --credential-set aad_auth'
    ]

    assert command == expected_command


@patch('resources.commands.get_porter_parameter_keys')
async def test_build_porter_command_user_parameters(mock_get_porter_parameter_keys, payload, config):
    mock_get_porter_parameter_keys.return_value = ["user_email", "user_name"]

    msg_body = payload

    command = await build_porter_command(config, msg_body)

    expected_command = [
        'porter some_action "resource123" --reference myregistry.azurecr.io/Resource Name:v1.0 --param user_email="john.doe@example.com" --param user_name="John Doe" --force --credential-set arm_auth --credential-set aad_auth'
    ]

    assert command == expected_command
