from collections import defaultdict
import json
import socket
import asyncio
import logging
from resource_processor.shared.config import ProcessorConfig

from shared.logging import disable_unwanted_loggers, initialize_logging, get_message_id_logger, shell_output_logger  # pylint: disable=import-error # noqa
from resources import strings  # pylint: disable=import-error # noqa
from contextlib import asynccontextmanager
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient, AutoLockRenewer
from azure.identity.aio import DefaultAzureCredential


# Initialise logging
logger_adapter = initialize_logging(logging.INFO, socket.gethostname())
disable_unwanted_loggers()

# Initialise config
config = ProcessorConfig(logger_adapter)

# Specify pass and fail status strings so we can return the right statuses to the api depending on the action type (with a default of custom action)
failed_status_string_for = defaultdict(lambda: strings.RESOURCE_ACTION_STATUS_FAILED, {
    "install": strings.RESOURCE_STATUS_FAILED,
    "uninstall": strings.RESOURCE_STATUS_DELETING_FAILED
})

pass_status_string_for = defaultdict(lambda: strings.RESOURCE_ACTION_STATUS_SUCCEEDED, {
    "install": strings.RESOURCE_STATUS_DEPLOYED,
    "uninstall": strings.RESOURCE_STATUS_DELETED
})


@asynccontextmanager
async def default_credentials(msi_id):
    """
    Context manager which yields the default credentials.
    """
    credential = DefaultAzureCredential(managed_identity_client_id=msi_id) if msi_id else DefaultAzureCredential()
    yield credential
    await credential.close()


async def receive_message(service_bus_client):
    """
    This method is an async generator which receives messages from service bus
    and yields those messages. If the yielded function return True the message is
    marked complete.
    """
    async with service_bus_client:
        q_name = config.resource_request_queue
        renewer = AutoLockRenewer(max_lock_renewal_duration=1800)
        receiver = service_bus_client.get_queue_receiver(queue_name=q_name, auto_lock_renewer=renewer)

        async with receiver:
            received_msgs = await receiver.receive_messages(max_message_count=10, max_wait_time=5)

            for msg in received_msgs:
                result = True
                message = ""

                try:
                    message = json.loads(str(msg))
                    result = (yield message)
                except (json.JSONDecodeError) as e:
                    logging.error(f"Received bad service bus resource request message: {e}")
                if result:
                    logging.info(f"Resource request for {message} is complete")
                else:
                    logging.error('Message processing failed!')
                logger_adapter.info(f"Message with id = {message['id']} processed as {result} and marked complete.")
                await receiver.complete_message(msg)


def azure_login_command():
    local_login = None
    # If running locally with use_local_creds enabled, use signed-in identity for authenticating with Service Bus
    if config.use_local_creds == "true":
        local_login = f"az account set --subscription {config.arm_subscription_id}"

    # If running locally with use_local_creds disabled, use the Service Principal credentials
    else:
        local_login = f"az login --service-principal --username {config.arm_client_id} --password {config.arm_client_secret} --tenant {config.arm_tenant_id}"

    # Use the Managed Identity when in VMSS identity
    vmss_login = f"az login --identity -u {config.vmss_msi_id}"
    command = vmss_login if config.vmss_msi_id else local_login
    return command


def azure_acr_login_command():
    return f"az acr login --name {config.registry_server.replace('.azurecr.io','')}"


async def get_porter_parameter_keys(msg_body):
    command = [f"{azure_login_command()} >/dev/null && \
        {azure_acr_login_command()} >/dev/null && \
        porter explain --reference {config.registry_server}/{msg_body['name']}:v{msg_body['version']} -ojson"]
    proc = await asyncio.create_subprocess_shell(
        ''.join(command),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=config.porter_env)

    stdout, stderr = await proc.communicate()
    logging.info(f'get_porter_parameter_keys exited with {proc.returncode}]')
    result_stdout = None
    result_stderr = None
    if stdout:
        result_stdout = stdout.decode()
        porter_explain_parameters = json.loads(result_stdout)["parameters"]
        porter_parameter_keys = [item["name"] for item in porter_explain_parameters]
        return porter_parameter_keys
    if stderr:
        result_stderr = stderr.decode()
        shell_output_logger(result_stderr, '[stderr]', logger_adapter, logging.WARN)


def get_installation_id(msg_body):
    # this will be used to identify each bundle install within the porter state store.
    return msg_body['id']


async def build_porter_command(msg_body, custom_action=False):
    porter_parameter_keys = await get_porter_parameter_keys(msg_body)
    porter_parameters = ""

    if porter_parameter_keys is None:
        logger_adapter.warning("Unknown porter parameters - explain probably failed.")
    else:
        for parameter_name in porter_parameter_keys:
            # try to find the param in order of priorities:
            # 1. msg parameters collection
            # 2. config (e.g. terraform state env vars)
            # 3. msg body root (e.g. id of the resource)
            parameter_value = msg_body['parameters'].get(
                parameter_name,
                config[parameter_name] if hasattr(config, parameter_name) else msg_body.get(parameter_name))

            # if still not found, might be a special case
            # (we give a chance to the method above to allow override of the special handeling done below)
            if parameter_value is None:
                parameter_value = get_special_porter_param_value(parameter_name, msg_body)

            # only append if we have a value, porter will complain anyway about missing parameters
            if parameter_value is not None:
                porter_parameters = porter_parameters + f" --param {parameter_name}=\"{parameter_value}\""

    installation_id = get_installation_id(msg_body)

    command_line = [f"{azure_login_command()} && {azure_acr_login_command()} && porter "
                    # If a custom action (i.e. not install, uninstall, upgrade) we need to use 'invoke'
                    f"{'invoke --action ' if custom_action else ''}"
                    f"{msg_body['action']} \"{installation_id}\" "
                    f" --reference {config.registry_server}/{msg_body['name']}:v{msg_body['version']}"
                    f" {porter_parameters} --cred ./vmss_porter/azure.json --allow-docker-host-access --force"
                    f" && porter show {installation_id}"]
    return command_line


def get_special_porter_param_value(parameter_name: str, msg_body):
    # some parameters might not have identical names and this comes to handle that
    if parameter_name == "mgmt_acr_name":
        return config.registry_server.replace('.azurecr.io', '')
    if parameter_name == "mgmt_resource_group_name":
        return config.tfstate_resource_group_name
    if parameter_name == "workspace_id":
        return msg_body.get("workspaceId")  # not included in all messgaes
    if parameter_name == "parent_service_id":
        return msg_body.get("parentWorkspaceServiceId")  # not included in all messgaes


async def build_porter_command_for_outputs(msg_body):
    installation_id = get_installation_id(msg_body)
    # we only need "real" outputs and use jq to remove the logs which are big
    command_line = [f"porter show {installation_id} --output json | jq -c '. | select(.Outputs!=null) | .Outputs | del (.[] | select(.Name==\"io.cnab.outputs.invocationImageLogs\"))'"]
    return command_line


async def run_porter(command):
    proc = await asyncio.create_subprocess_shell(
        ''.join(command),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=config.porter_env)

    stdout, stderr = await proc.communicate()
    logging.info(f'run porter exited with {proc.returncode}]')
    result_stdout = None
    result_stderr = None
    if stdout:
        result_stdout = stdout.decode()
        shell_output_logger(result_stderr, '[stdout]', logger_adapter, logging.INFO)

    if stderr:
        result_stderr = stderr.decode()
        shell_output_logger(result_stderr, '[stderr]', logger_adapter, logging.WARN)

    return (proc.returncode, result_stdout, result_stderr)


def service_bus_message_generator(sb_message, status, deployment_message, outputs=None):
    installation_id = get_installation_id(sb_message)
    message_dict = {
        "operationId": sb_message["operationId"],
        "id": sb_message["id"],
        "status": status,
        "message": f"{installation_id}: {deployment_message}"}

    if outputs is not None:
        message_dict["outputs"] = outputs

    resource_request_message = json.dumps(message_dict)
    return resource_request_message


async def invoke_porter_action(msg_body, sb_client, message_logger_adapter) -> bool:
    """
    Handle resource message by invoking specified porter action (i.e. install, uninstall)
    """
    installation_id = get_installation_id(msg_body)
    action = msg_body["action"]
    message_logger_adapter.info(f"{installation_id}: {action} action configuration starting")
    sb_sender = sb_client.get_queue_sender(queue_name=config.deployment_status_queue)

    # If the action is install, post message on sb queue to start a deployment job
    if action == "install":
        resource_request_message = service_bus_message_generator(msg_body, strings.RESOURCE_STATUS_DEPLOYING, "Deployment job starting")
        await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"]))

    # Build and run porter command (flagging if its a built-in action or custom so we can adapt porter command appropriately)
    is_custom_action = action not in ["install", "upgrade", "uninstall"]
    porter_command = await build_porter_command(msg_body, is_custom_action)
    returncode, _, err = await run_porter(porter_command)

    # Handle command output
    if returncode != 0:
        error_message = "Error context message = " + " ".join(err.split('\n')) + " ; Command executed: ".join(porter_command)
        resource_request_message = service_bus_message_generator(msg_body, failed_status_string_for[action], error_message)

        # Post message on sb queue to notify receivers of action failure
        await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"]))
        message_logger_adapter.info(f"{installation_id}: Porter action failed with error = {error_message}")
        return False

    else:
        # Get the outputs
        # TODO: decide if this should "fail" the deployment
        _, outputs = await get_porter_outputs(msg_body, message_logger_adapter)

        success_message = f"{action} action completed successfully."
        resource_request_message = service_bus_message_generator(msg_body, pass_status_string_for[action], success_message, outputs)

        await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"]))
        message_logger_adapter.info(f"{installation_id}: {success_message}")
        return True


async def get_porter_outputs(msg_body, message_logger_adapter):
    porter_command = await build_porter_command_for_outputs(msg_body)
    returncode, stdout, err = await run_porter(porter_command)

    if returncode != 0:
        error_message = "Error context message = " + " ".join(err.split('\n'))
        message_logger_adapter.info(f"{get_installation_id(msg_body)}: Failed to get outputs with error = {error_message}")
        return False, ""
    else:
        outputs_json = {}
        try:
            outputs_json = json.loads(stdout)
            logger_adapter.info(f"Got outputs as json: {outputs_json}")
        except ValueError:
            logger_adapter.info(f"Got outputs invalid json: {stdout}")

        return True, outputs_json


async def runner():
    async with default_credentials(config.vmss_msi_id) as credential:
        service_bus_client = ServiceBusClient(config.service_bus_namespace, credential)
        logger_adapter.info("Starting message receiving loop...")

        while True:
            logger_adapter.info("Checking for new messages...")
            receive_message_gen = receive_message(service_bus_client)

            try:
                async for message in receive_message_gen:
                    logger_adapter.info(f"Message received with id={message['id']}")
                    message_logger_adapter = get_message_id_logger(message['id'])  # logger includes message id in every entry.
                    result = await invoke_porter_action(message, service_bus_client, message_logger_adapter)
                    await receive_message_gen.asend(result)

            except StopAsyncIteration:  # the async generator when finished signals end with this exception.
                pass

            logger_adapter.info("All messages processed. Sleeping...")
            await asyncio.sleep(60)


if __name__ == "__main__":
    logger_adapter.info("Started resource processor")
    asyncio.run(runner())
