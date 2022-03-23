import threading
import json
import socket
import asyncio
import logging
import sys
from resources.commands import build_porter_command, build_porter_command_for_outputs
from shared.config import get_config
from resources.helpers import get_installation_id
from resources.httpserver import start_server

from shared.logging import disable_unwanted_loggers, initialize_logging, get_message_id_logger, shell_output_logger  # pylint: disable=import-error # noqa
from resources import strings, statuses  # pylint: disable=import-error # noqa
from contextlib import asynccontextmanager
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient, AutoLockRenewer
from azure.identity.aio import DefaultAzureCredential


# Initialise logging
logger_adapter = initialize_logging(logging.INFO, socket.gethostname())
disable_unwanted_loggers()

# Initialise config
try:
    config = get_config()
except KeyError as e:
    logger_adapter.error(f"Environment variable {e} is not set correctly...Exiting")
    sys.exit(1)


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
        q_name = config["resource_request_queue"]
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


async def run_porter(command):
    """
    Run a Porter command
    """
    proc = await asyncio.create_subprocess_shell(
        ''.join(command),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=config["porter_env"])

    stdout, stderr = await proc.communicate()
    logging.info(f'run porter exited with {proc.returncode}')
    result_stdout = None
    result_stderr = None

    if stdout:
        result_stdout = stdout.decode()
        shell_output_logger(result_stdout, '[stdout]', logger_adapter, logging.INFO)

    if stderr:
        result_stderr = stderr.decode()
        shell_output_logger(result_stderr, '[stderr]', logger_adapter, logging.WARN)

    return (proc.returncode, result_stdout, result_stderr)


def service_bus_message_generator(sb_message, status, deployment_message, outputs=None):
    """
    Generate a resource request message
    """
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
    message_logger_adapter.info(f"{installation_id}: {action} action starting...")
    sb_sender = sb_client.get_queue_sender(queue_name=config["deployment_status_queue"])

    # If the action is install/upgrade, post message on sb queue to start a deployment job
    if action == "install" or action == "upgrade":
        resource_request_message = service_bus_message_generator(msg_body, strings.RESOURCE_STATUS_DEPLOYING, "Deployment job starting")
        await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"]))

    # Build and run porter command (flagging if its a built-in action or custom so we can adapt porter command appropriately)
    is_custom_action = action not in ["install", "upgrade", "uninstall"]
    porter_command = await build_porter_command(config, message_logger_adapter, msg_body, is_custom_action)
    returncode, _, err = await run_porter(porter_command)

    # Handle command output
    if returncode != 0:
        error_message = "Error context message = " + " ".join(err.split('\n')) + " ; Command executed: ".join(porter_command)
        resource_request_message = service_bus_message_generator(msg_body, statuses.failed_status_string_for[action], error_message)

        # Post message on sb queue to notify receivers of action failure
        await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"]))
        message_logger_adapter.info(f"{installation_id}: Porter action failed with error = {error_message}")
        return False

    else:
        # Get the outputs
        # TODO: decide if this should "fail" the deployment
        _, outputs = await get_porter_outputs(msg_body, message_logger_adapter)

        success_message = f"{action} action completed successfully."
        resource_request_message = service_bus_message_generator(msg_body, statuses.pass_status_string_for[action], success_message, outputs)

        await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"]))
        message_logger_adapter.info(f"{installation_id}: {success_message}")
        return True


async def get_porter_outputs(msg_body, message_logger_adapter):
    """
    Get outputs JSON from a Porter command
    """
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
            message_logger_adapter.info(f"Got outputs as json: {outputs_json}")
        except ValueError:
            message_logger_adapter.error(f"Got outputs invalid json: {stdout}")

        return True, outputs_json


async def runner():
    async with default_credentials(config["vmss_msi_id"]) as credential:
        service_bus_client = ServiceBusClient(config["service_bus_namespace"], credential)
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
    httpserver_thread = threading.Thread(target=start_server)
    httpserver_thread.start()
    logger_adapter.info("Started http server")

    asyncio.ensure_future(runner())
    event_loop = asyncio.get_event_loop()
    event_loop.run_forever()
    logger_adapter.info("Started resource processor")
