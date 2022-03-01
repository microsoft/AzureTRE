import os
import sys
import json
import socket
import asyncio
import logging

from shared.logging import disable_unwanted_loggers, initialize_logging, get_message_id_logger, shell_output_logger  # pylint: disable=import-error # noqa
from resources import strings  # pylint: disable=import-error # noqa
from contextlib import asynccontextmanager
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient, AutoLockRenewer
from azure.identity.aio import DefaultAzureCredential

logger_adapter = initialize_logging(logging.INFO, socket.gethostname())
disable_unwanted_loggers()

failed_status_string_for = {
    "install": strings.RESOURCE_STATUS_FAILED,
    "uninstall": strings.RESOURCE_STATUS_DELETING_FAILED
}

pass_status_string_for = {
    "install": strings.RESOURCE_STATUS_DEPLOYED,
    "uninstall": strings.RESOURCE_STATUS_DELETED
}


@asynccontextmanager
async def default_credentials(msi_id):
    """
    Context manager which yields the default credentials.
    """
    credential = DefaultAzureCredential(managed_identity_client_id=msi_id) if msi_id else DefaultAzureCredential()
    yield credential
    await credential.close()


async def receive_message(env_vars, service_bus_client):
    """
    This method is an async generator which receives messages from service bus
    and yields those messages. If the yielded function return True the message is
    marked complete.
    """
    async with service_bus_client:
        q_name = env_vars["resource_request_queue"]
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


def azure_login_command(env_vars):
    local_login = f"az login --service-principal --username {env_vars['arm_client_id']} --password {env_vars['arm_client_secret']} --tenant {env_vars['arm_tenant_id']}"
    vmss_login = f"az login --identity -u {env_vars['vmss_msi_id']}"
    command = vmss_login if env_vars['vmss_msi_id'] else local_login
    return command


def azure_acr_login_command(env_vars):
    return f"az acr login --name {env_vars['registry_server'].replace('.azurecr.io','')}"


async def get_porter_parameter_keys(msg_body, env_vars):
    command = [f"{azure_login_command(env_vars)} >/dev/null && \
        {azure_acr_login_command(env_vars)} >/dev/null && \
        porter explain --reference {env_vars['registry_server']}/{msg_body['name']}:v{msg_body['version']} -ojson"]
    proc = await asyncio.create_subprocess_shell(
        ''.join(command),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=porter_envs(env_vars))

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


async def build_porter_command(msg_body, env_vars):
    porter_parameter_keys = await get_porter_parameter_keys(msg_body, env_vars)
    porter_parameters = ""

    if porter_parameter_keys is None:
        logger_adapter.warning("Unknown proter parameters - explain probably failed.")
    else:
        for parameter_name in porter_parameter_keys:
            # try to find the param in order of priorities:
            # 1. msg parameters collection
            # 2. env_vars (e.g. terraform state ones)
            # 3. msg body root (e.g. id of the resource)
            parameter_value = msg_body['parameters'].get(
                parameter_name,
                env_vars.get(
                    parameter_name,
                    msg_body.get(parameter_name)))

            # if still not found, might be a special case
            # (we give a chance to the method above to allow override of the special handeling done below)
            if parameter_value is None:
                parameter_value = get_special_porter_param_value(parameter_name, msg_body, env_vars)

            # only append if we have a value, porter will complain anyway about missing parameters
            if parameter_value is not None:
                porter_parameters = porter_parameters + f" --param {parameter_name}=\"{parameter_value}\""

    installation_id = get_installation_id(msg_body)

    command_line = [f"{azure_login_command(env_vars)} && {azure_acr_login_command(env_vars)} && porter "
                    f"{msg_body['action']} \"{installation_id}\" "
                    f" --reference {env_vars['registry_server']}/{msg_body['name']}:v{msg_body['version']}"
                    f" {porter_parameters} --cred ./vmss_porter/azure.json --allow-docker-host-access --force"
                    f" && porter show {installation_id}"]
    return command_line


def get_special_porter_param_value(parameter_name: str, msg_body, env_vars):
    # some parameters might not have identical names and this comes to handle that
    if parameter_name == "mgmt_acr_name":
        return env_vars['registry_server'].replace('.azurecr.io', '')
    if parameter_name == "mgmt_resource_group_name":
        return env_vars['tfstate_resource_group_name']
    if parameter_name == "workspace_id":
        return msg_body.get("workspaceId")  # not included in all messgaes
    if parameter_name == "parent_service_id":
        return msg_body.get("parentWorkspaceServiceId")  # not included in all messgaes


async def build_porter_command_for_outputs(msg_body):
    installation_id = get_installation_id(msg_body)
    # we only need "real" outputs and use jq to remove the logs which are big
    command_line = [f"porter show {installation_id} --output json | jq -c '. | select(.Outputs!=null) | .Outputs | del (.[] | select(.Name==\"io.cnab.outputs.invocationImageLogs\"))'"]
    return command_line


def porter_envs(env_var):
    porter_env_vars = {}
    porter_env_vars["HOME"] = os.environ['HOME']
    porter_env_vars["PATH"] = os.environ['PATH']
    porter_env_vars["ARM_CLIENT_ID"] = env_var["arm_client_id"]
    porter_env_vars["ARM_CLIENT_SECRET"] = env_var["arm_client_secret"]
    porter_env_vars["ARM_SUBSCRIPTION_ID"] = env_var["arm_subscription_id"]
    porter_env_vars["ARM_TENANT_ID"] = env_var["arm_tenant_id"]

    return porter_env_vars


async def run_porter(command, env_vars):
    proc = await asyncio.create_subprocess_shell(
        ''.join(command),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=porter_envs(env_vars))

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


async def deploy_porter_bundle(msg_body, sb_client, env_vars, message_logger_adapter):
    installation_id = get_installation_id(msg_body)
    job_type = "Deployment" if msg_body['action'] == "install" else "Deleting"
    message_logger_adapter.info(f"{installation_id}: {job_type} job configuration starting")
    sb_sender = sb_client.get_queue_sender(queue_name=env_vars["deployment_status_queue"])
    if job_type == "Deployment":
        resource_request_message = service_bus_message_generator(msg_body, strings.RESOURCE_STATUS_DEPLOYING, "Deployment job starting")
        await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"]))
    porter_command = await build_porter_command(msg_body, env_vars)
    returncode, _, err = await run_porter(porter_command, env_vars)
    if returncode != 0:
        error_message = "Error context message = " + " ".join(err.split('\n')) + " ; Command executed: ".join(porter_command)
        resource_request_message = service_bus_message_generator(msg_body, failed_status_string_for[msg_body['action']], error_message)
        await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"]))
        message_logger_adapter.info(f"{installation_id}: Deployment job configuration failed error = {error_message}")
        return False
    else:
        # Get the outputs
        # TODO: decide if this should "fail" the deployment
        _, outputs = await get_porter_outputs(msg_body, env_vars, message_logger_adapter)

        success_message = f"{job_type} completed successfully."
        resource_request_message = service_bus_message_generator(msg_body, pass_status_string_for[msg_body['action']], success_message, outputs)
        await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"]))
        message_logger_adapter.info(f"{installation_id}: {success_message}")
        return True


async def get_porter_outputs(msg_body, env_vars, message_logger_adapter):
    porter_command = await build_porter_command_for_outputs(msg_body)
    returncode, stdout, err = await run_porter(porter_command, env_vars)
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


async def runner(env_vars):
    msi_id = env_vars["vmss_msi_id"]
    service_bus_namespace = env_vars["service_bus_namespace"]
    async with default_credentials(msi_id) as credential:
        service_bus_client = ServiceBusClient(service_bus_namespace, credential)
        logger_adapter.info("Starting message receiving loop...")
        while True:
            logger_adapter.info("Checking for new messages...")
            receive_message_gen = receive_message(env_vars, service_bus_client)
            try:
                async for message in receive_message_gen:
                    logger_adapter.info(f"Message received for id={message['id']}")
                    message_logger_adapter = get_message_id_logger(message['id'])  # logger includes message id in every entry.
                    result = await deploy_porter_bundle(message, service_bus_client, env_vars, message_logger_adapter)
                    await receive_message_gen.asend(result)
            except StopAsyncIteration:  # the async generator when finished signals end with this exception.
                pass
            logger_adapter.info("All messages done sleeping...")
            await asyncio.sleep(60)


def read_env_vars():
    env_vars = {
        # Needed for local dev
        "app_id": os.environ.get("AZURE_CLIENT_ID", None),
        "app_password": os.environ.get("AZURE_CLIENT_SECRET", None),

        "registry_server": os.environ["REGISTRY_SERVER"],
        "tfstate_container_name": os.environ['TERRAFORM_STATE_CONTAINER_NAME'],
        "tfstate_resource_group_name": os.environ['MGMT_RESOURCE_GROUP_NAME'],
        "tfstate_storage_account_name": os.environ['MGMT_STORAGE_ACCOUNT_NAME'],
        "deployment_status_queue": os.environ['SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE'],
        "resource_request_queue": os.environ['SERVICE_BUS_RESOURCE_REQUEST_QUEUE'],
        "service_bus_namespace": os.environ['SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE'],
        "vmss_msi_id": os.environ.get('VMSS_MSI_ID', None),

        # Needed for running porter
        "arm_use_msi": os.environ["ARM_USE_MSI"],
        "arm_subscription_id": os.environ['ARM_SUBSCRIPTION_ID'],
        "arm_client_id": os.environ["ARM_CLIENT_ID"],
        "arm_tenant_id": os.environ["ARM_TENANT_ID"]
    }

    env_vars["arm_client_secret"] = os.environ["ARM_CLIENT_SECRET"] if env_vars["arm_use_msi"] == "false" else ""

    return env_vars


if __name__ == "__main__":
    try:
        env_vars = read_env_vars()
    except KeyError as e:
        logger_adapter.error(f"Environment variable {e} is not set correctly...Exiting")
        sys.exit(1)
    logger_adapter.info("Started processor")
    asyncio.run(runner(env_vars))
