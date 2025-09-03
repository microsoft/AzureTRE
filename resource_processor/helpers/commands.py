import asyncio
import json
import base64
import logging
from urllib.parse import urlparse

from shared.logging import logger, shell_output_logger


async def run_command_helper(cmd_parts: list, config: dict, description: str):
    logger.debug(f"Executing {description}")

    proc = await asyncio.create_subprocess_exec(
        *cmd_parts,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=config["porter_env"]
    )

    stdout, stderr = await proc.communicate()

    stdout_text = None
    stderr_text = None

    if stdout:
        stdout_text = stdout.decode()
        shell_output_logger(stdout_text, '[stdout]', logging.INFO)

    if stderr:
        stderr_text = stderr.decode()
        shell_output_logger(stderr_text, '[stderr]', logging.WARN)

    if proc.returncode != 0:
        logger.error(f"{description} failed with return code {proc.returncode}")
    else:
        logger.debug(f"{description} completed successfully")

    return (proc.returncode, stdout_text, stderr_text)


def azure_login_command(config):
    commands = [
        ["az", "cloud", "set", "--name", config['azure_environment']]
    ]

    if config.get("vmss_msi_id"):
        # Use the Managed Identity when in VMSS context
        commands.append(["az", "login", "--identity", "-u", config['vmss_msi_id']])
    else:
        # Use a Service Principal when running locally
        commands.append(["az", "login", "--service-principal",
                         "--username", config['arm_client_id'],
                         "--password", config['arm_client_secret'],
                         "--tenant", config['arm_tenant_id']])

    return commands


def apply_porter_credentials_sets_command(config):
    commands = []

    if config.get("vmss_msi_id"):
        # Use the Managed Identity when in VMSS context
        commands.append(["porter", "credentials", "apply", "vmss_porter/arm_auth_local_debugging.json"])
        commands.append(["porter", "credentials", "apply", "vmss_porter/aad_auth.json"])
    else:
        # Use a Service Principal when running locally
        commands.append(["porter", "credentials", "apply", "vmss_porter/arm_auth_local_debugging.json"])
        commands.append(["porter", "credentials", "apply", "vmss_porter/aad_auth_local_debugging.json"])

    return commands


def azure_acr_login_command(config):
    acr_name = _get_acr_name(acr_fqdn=config['registry_server'])
    return [["az", "acr", "login", "--name", acr_name]]


async def build_porter_command(config, msg_body, custom_action=False):
    porter_parameter_keys = await get_porter_parameter_keys(config, msg_body)
    porter_parameters = []

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

                porter_parameters.extend(["--param", f"{parameter_name}={parameter_value}"])

    installation_id = msg_body['id']

    command = ["porter"]
    if custom_action:
        command.extend(["invoke", "--action"])

    command.append(msg_body['action'])
    command.append(installation_id)
    command.extend([
        "--reference",
        f"{config['registry_server']}/{msg_body['name']}:v{msg_body['version']}"
    ])
    command.extend(porter_parameters)
    command.append("--force")
    command.extend(["--credential-set", "arm_auth"])
    command.extend(["--credential-set", "aad_auth"])

    if msg_body['action'] == 'upgrade':
        command.append("--force-upgrade")

    return [command]


async def build_porter_command_for_outputs(msg_body):
    installation_id = msg_body['id']
    command = [
        "porter",
        "installations",
        "output",
        "list",
        "--installation",
        installation_id,
        "--output",
        "json"
    ]
    return [command]


async def get_porter_parameter_keys(config, msg_body):
    login_commands = azure_login_command(config)
    for cmd in login_commands:
        returncode, _, _ = await run_command_helper(cmd, config, "Azure login for Porter explain")
        if returncode != 0:
            return None

    acr_login_commands = azure_acr_login_command(config)
    for cmd in acr_login_commands:
        returncode, _, _ = await run_command_helper(cmd, config, "Azure ACR login for Porter explain")
        if returncode != 0:
            return None

    explain_cmd = [
        "porter",
        "explain",
        "--reference",
        f"{config['registry_server']}/{msg_body['name']}:v{msg_body['version']}",
        "--output",
        "json"
    ]

    returncode, stdout_text, _ = await run_command_helper(explain_cmd, config, "Porter explain command")

    if returncode != 0 or not stdout_text:
        return None

    try:
        porter_explain_parameters = json.loads(stdout_text)["parameters"]
        porter_parameter_keys = [item["name"] for item in porter_explain_parameters]
        return porter_parameter_keys
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse Porter explain output: {e}")
        return None


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
