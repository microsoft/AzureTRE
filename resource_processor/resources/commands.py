import asyncio
import json
import logging
import base64

from resources.helpers import get_installation_id
from shared.logging import shell_output_logger


def azure_login_command(config):
    # Use a Service Principal when running locally
    local_login = f"az login --service-principal --username {config['arm_client_id']} --password {config['arm_client_secret']} --tenant {config['arm_tenant_id']}"

    # Use the Managed Identity when in VMSS context
    vmss_login = f"az login --identity -u {config['vmss_msi_id']}"

    command = vmss_login if config["vmss_msi_id"] else local_login
    return command


def azure_acr_login_command(config):
    return f"az acr login --name {config['registry_server'].replace('.azurecr.io','')}"


async def build_porter_command(config, logger, msg_body, custom_action=False):
    porter_parameter_keys = await get_porter_parameter_keys(config, logger, msg_body)
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

    command_line = [f"{azure_login_command(config)} && {azure_acr_login_command(config)} && porter "
                    # If a custom action (i.e. not install, uninstall, upgrade) we need to use 'invoke'
                    f"{'invoke --action ' if custom_action else ''}"
                    f"{msg_body['action']} \"{installation_id}\" "
                    f" --reference {config['registry_server']}/{msg_body['name']}:v{msg_body['version']}"
                    f" {porter_parameters} --allow-docker-host-access --force"
                    f" --cred ./vmss_porter/arm_auth_local_debugging.json"
                    f" --cred ./vmss_porter/aad_auth.json"
                    ]
    return command_line


async def build_porter_command_for_outputs(msg_body):
    installation_id = get_installation_id(msg_body)
    # we only need "real" outputs and use jq to remove the logs which are big
    command_line = [f"porter installations output list --installation {installation_id} --output json | jq -c 'del (.[] | select(.Name==\"io.cnab.outputs.invocationImageLogs\"))'"]
    return command_line


async def get_porter_parameter_keys(config, logger, msg_body):
    command = [f"{azure_login_command(config)} >/dev/null && \
        {azure_acr_login_command(config)} >/dev/null && \
        porter explain --reference {config['registry_server']}/{msg_body['name']}:v{msg_body['version']} --output json"]

    proc = await asyncio.create_subprocess_shell(
        ''.join(command),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=config["porter_env"])

    stdout, stderr = await proc.communicate()
    logging.info(f'get_porter_parameter_keys exited with {proc.returncode}')
    result_stdout = None
    result_stderr = None

    if stdout:
        result_stdout = stdout.decode()
        porter_explain_parameters = json.loads(result_stdout)["parameters"]
        porter_parameter_keys = [item["name"] for item in porter_explain_parameters]
        return porter_parameter_keys
    if stderr:
        result_stderr = stderr.decode()
        shell_output_logger(result_stderr, '[stderr]', logger, logging.WARN)


def get_special_porter_param_value(config, parameter_name: str, msg_body):
    # some parameters might not have identical names and this comes to handle that
    if parameter_name == "mgmt_acr_name":
        return config["registry_server"].replace('.azurecr.io', '')
    if parameter_name == "mgmt_resource_group_name":
        return config["tfstate_resource_group_name"]
    if parameter_name == "workspace_id":
        return msg_body.get("workspaceId")  # not included in all messages
    if parameter_name == "parent_service_id":
        return msg_body.get("parentWorkspaceServiceId")  # not included in all messages
