import asyncio
import json
import base64
import logging
from urllib.parse import urlparse

from resources.helpers import get_installation_id
from shared.logging import logger, shell_output_logger


def azure_login_command(config):
    set_cloud_command = f"az cloud set --name {config['azure_environment']} >/dev/null "

    if config["vmss_msi_id"]:
        # Use the Managed Identity when in VMSS context
        login_command = f"az login --identity -u {config['vmss_msi_id']} >/dev/null "

    else:
        # Use a Service Principal when running locally
        login_command = f"az login --service-principal --username {config['arm_client_id']} --password {config['arm_client_secret']} --tenant {config['arm_tenant_id']} >/dev/null"

    return f"{set_cloud_command} && {login_command}"


def apply_porter_credentials_sets_command(config):
    if config["vmss_msi_id"]:
        # Use the Managed Identity when in VMSS context
        porter_credential_sets = "porter credentials apply vmss_porter/arm_auth_local_debugging.json >/dev/null 2>&1 && porter credentials apply vmss_porter/aad_auth.json >/dev/null 2>&1"

    else:
        # Use a Service Principal when running locally
        porter_credential_sets = "porter credentials apply vmss_porter/arm_auth_local_debugging.json >/dev/null 2>&1 && porter credentials apply vmss_porter/aad_auth_local_debugging.json >/dev/null 2>&1"

    return f"{porter_credential_sets}"


def azure_acr_login_command(config):
    acr_name = _get_acr_name(acr_fqdn=config['registry_server'])
    return f"az acr login --name {acr_name} >/dev/null "


async def build_porter_command(config, msg_body, custom_action=False):
    porter_parameter_keys = await get_porter_parameter_keys(config, msg_body)
    porter_parameters = ""

    if porter_parameter_keys is None:
        logger.warning("Unknown porter parameters - explain probably failed.")
    else:
        for parameter_name in porter_parameter_keys:
            # try to find the param in order of priorities:
            parameter_value = None

            # 1. msg parameters collection
            if parameter_name in msg_body["parameters"]:
                parameter_value = msg_body["parameters"][parameter_name]

            # 2. config (e.g. terraform state env vars)
            elif parameter_name in config:
                parameter_value = config[parameter_name]

            # 3. msg body root (e.g. id of the resource)
            elif parameter_name in msg_body:
                parameter_value = msg_body[parameter_name]

            # 4. if starts user_ then look in user object
            elif parameter_name.startswith("user_") and "user" in msg_body and parameter_name[5:] in msg_body["user"]:
                parameter_value = msg_body["user"][parameter_name[5:]]

            # if still not found, might be a special case
            # (we give a chance to the method above to allow override of the special handeling done below)
            else:
                parameter_value = get_special_porter_param_value(config, parameter_name, msg_body)

            # only append if we have a value, porter will complain anyway about missing parameters
            if parameter_value is not None:
                if isinstance(parameter_value, dict) or isinstance(parameter_value, list):
                    # base64 encode complex types to pass in safely
                    val = json.dumps(parameter_value)
                    val_bytes = val.encode("ascii")
                    val_base64_bytes = base64.b64encode(val_bytes)
                    parameter_value = val_base64_bytes.decode("ascii")

                porter_parameters = porter_parameters + f" --param {parameter_name}=\"{parameter_value}\""

    installation_id = get_installation_id(msg_body)

    command_line = [f"porter"
                    # If a custom action (i.e. not install, uninstall, upgrade) we need to use 'invoke'
                    f"{' invoke --action' if custom_action else ''}"
                    f" {msg_body['action']} \"{installation_id}\""
                    f" --reference {config['registry_server']}/{msg_body['name']}:v{msg_body['version']}"
                    f" {porter_parameters} --force"
                    f" --credential-set arm_auth"
                    f" --credential-set aad_auth"
                    ]

    return command_line


async def build_porter_command_for_outputs(msg_body):
    installation_id = get_installation_id(msg_body)
    command_line = [f"porter installations output list --installation {installation_id} --output json"]
    return command_line


async def get_porter_parameter_keys(config, msg_body):
    command = [f"{azure_login_command(config)} && \
        {azure_acr_login_command(config)} && \
        porter explain --reference {config['registry_server']}/{msg_body['name']}:v{msg_body['version']} --output json"]

    proc = await asyncio.create_subprocess_shell(
        ''.join(command),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=config["porter_env"])

    stdout, stderr = await proc.communicate()
    logger.debug(f'get_porter_parameter_keys exited with {proc.returncode}')
    result_stdout = None
    result_stderr = None

    if stdout:
        result_stdout = stdout.decode()
        porter_explain_parameters = json.loads(result_stdout)["parameters"]
        porter_parameter_keys = [item["name"] for item in porter_explain_parameters]
        return porter_parameter_keys
    if stderr:
        result_stderr = stderr.decode()
        shell_output_logger(result_stderr, '[stderr]', logging.WARN)


def get_special_porter_param_value(config, parameter_name: str, msg_body):
    # some parameters might not have identical names and this comes to handle that
    if parameter_name == "mgmt_acr_name":
        return _get_acr_name(acr_fqdn=config['registry_server'])
    if parameter_name == "mgmt_resource_group_name":
        return config["tfstate_resource_group_name"]
    if parameter_name == "azure_environment":
        return config['azure_environment']
    if parameter_name == "workspace_id":
        return msg_body.get("workspaceId")  # not included in all messages
    if parameter_name == "parent_service_id":
        return msg_body.get("parentWorkspaceServiceId")  # not included in all messages
    if parameter_name == "owner_id":
        return msg_body.get("ownerId")  # not included in all messages
    if (value := config["bundle_params"].get(parameter_name.lower())) is not None:
        return value
    # Parameters that relate to the cloud type
    if parameter_name == "aad_authority_url":
        return config['aad_authority_url']
    if parameter_name == "microsoft_graph_fqdn":
        return urlparse(config['microsoft_graph_fqdn']).netloc
    if parameter_name == "arm_environment":
        return config["arm_environment"]


def _get_acr_name(acr_fqdn: str):
    return acr_fqdn.split('.', 1)[0]
