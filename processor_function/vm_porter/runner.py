import os
import sys
import json
import socket
import asyncio
import logging
from shared.logger import disable_unwanted_loggers, initialize_logging  # pylint: disable=import-error # noqa
from resources import strings
from contextlib import asynccontextmanager
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient, AutoLockRenewer
from azure.identity.aio import DefaultAzureCredential

logger_adapter = initialize_logging(logging.INFO, socket.gethostname())
disable_unwanted_loggers()


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
        renewer = AutoLockRenewer()
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


def build_porter_command(msg_body, env_vars):
    porter_parameters = ""
    for parameter in msg_body['parameters']:
        porter_parameters = porter_parameters + f" --param {parameter}={msg_body['parameters'][parameter]}"

    installation_id = msg_body['parameters']['tre_id'] + "-" + msg_body['parameters']['workspace_id']

    porter_parameters = porter_parameters + f" --param tfstate_container_name={env_vars['tfstate_container_name']}"
    porter_parameters = porter_parameters + f" --param tfstate_resource_group_name={env_vars['tfstate_resource_group_name']}"
    porter_parameters = porter_parameters + f" --param tfstate_storage_account_name={env_vars['tfstate_storage_account_name']}"

    command_line = [f"{azure_login_command(env_vars)} && az acr login --name {env_vars['registry_server']} && porter "
                    f"{msg_body['action']} {installation_id} "
                    f" --reference {env_vars['registry_server']}/{msg_body['name']}:v{msg_body['version']}"
                    f" {porter_parameters} --cred ./vm_porter/azure.json --allow-docker-host-access"
                    f" && porter show {installation_id}"]
    return command_line


def porter_envs(env_var):
    porter_env_vars = {}
    porter_env_vars["HOME"] = os.environ['HOME']
    porter_env_vars["PATH"] = os.environ['PATH']
    porter_env_vars["ARM_CLIENT_ID"] = env_var["arm_client_id"]
    porter_env_vars["ARM_CLIENT_SECRET"] = env_var["arm_client_secret"]
    porter_env_vars["ARM_SUBSCRIPTION_ID"] = env_var["arm_subscription_id"]
    porter_env_vars["ARM_TENANT_ID"] = env_var["arm_tenant_id"]
    porter_env_vars["PORTER_DRIVER"] = "docker"
    return porter_env_vars


async def run_porter(command, env_vars):
    proc = await asyncio.create_subprocess_shell(
        ''.join(command),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=porter_envs(env_vars))

    stdout, stderr = await proc.communicate()
    logging.info(f'[{command!r} exited with {proc.returncode}]')
    result_stdout = None
    result_stderr = None
    if stdout:
        result_stdout = stdout.decode()
        logger_adapter.info('[stdout]')
        for string in result_stdout.split('\n'):
            logger_adapter.info(string)
    if stderr:
        result_stderr = stderr.decode()
        logger_adapter.info('[stderr]')
        for string in result_stderr.split('\n'):
            logger_adapter.info(string)

    return (proc.returncode, result_stdout, result_stderr)


def service_bus_message_generator(sb_message, status, deployment_message):
    installation_id = sb_message['parameters']['tre_id'] + "-" + sb_message['parameters']['workspace_id']
    resource_request_message = json.dumps({
        "id": sb_message["id"],
        "status": status,
        "message": f"{installation_id}: {deployment_message}"
    })
    return resource_request_message


async def deploy_porter_bundle(msg_body, sb_client, env_vars, message_logger_adapter):
    installation_id = msg_body['parameters']['tre_id'] + "-" + msg_body['parameters']['workspace_id']
    message_logger_adapter.info(f"{installation_id}: Deployment job configuration starting")
    sb_sender = sb_client.get_queue_sender(queue_name=env_vars["deployment_status_queue"])
    resource_request_message = service_bus_message_generator(msg_body, strings.RESOURCE_STATUS_DEPLOYING, "Deployment job starting")
    await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"]))

    returncode, _, err = await run_porter(build_porter_command(msg_body, env_vars), env_vars)
    if returncode != 0:
        error_message = "Error context message = " + " ".join(err.split('\n'))
        resource_request_message = service_bus_message_generator(msg_body, strings.RESOURCE_STATUS_FAILED, error_message)
        await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"]))
        message_logger_adapter.info(f"{installation_id}: Deployment job configuration failed error = {error_message}")
        return False
    else:
        success_message = "Workspace was deployed successfully..."
        resource_request_message = service_bus_message_generator(msg_body, strings.RESOURCE_STATUS_DEPLOYED, success_message)
        await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"]))
        message_logger_adapter.info(f"{installation_id}: {success_message}")
        return True


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
                    message_logger_adapter = initialize_logging(logging.INFO, message['id'])
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
        "arm_subscription_id": os.environ['ARM_SUBSCRIPTION_ID'],
        "arm_client_id": os.environ["ARM_CLIENT_ID"],
        "arm_client_secret": os.environ["ARM_CLIENT_SECRET"],
        "arm_tenant_id": os.environ["ARM_TENANT_ID"],
    }
    return env_vars


if __name__ == "__main__":
    try:
        env_vars = read_env_vars()
    except KeyError as e:
        logger_adapter.error(f"Environment variable {e} is not set correctly...Exiting")
        sys.exit(1)
    logger_adapter.info("Started processor")
    asyncio.run(runner(env_vars))
