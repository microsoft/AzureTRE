from typing import Optional
from multiprocessing import Process
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
from shared.config import VERSION
from resources import strings, statuses  # pylint: disable=import-error # noqa
from contextlib import asynccontextmanager
from azure.servicebus import ServiceBusMessage, NEXT_AVAILABLE_SESSION
from azure.servicebus.exceptions import OperationTimeoutError, ServiceBusConnectionError
from azure.servicebus.aio import ServiceBusClient, AutoLockRenewer
from azure.identity.aio import DefaultAzureCredential


def set_up_logger(enable_console_logging: bool) -> logging.LoggerAdapter:
    # Initialise logging
    logger_adapter = initialize_logging(logging.INFO, socket.gethostname(), enable_console_logging)
    disable_unwanted_loggers()
    return logger_adapter


def set_up_config(logger_adapter: logging.LoggerAdapter) -> Optional[dict]:
    try:
        config = get_config(logger_adapter)
        return config
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


async def receive_message(service_bus_client, logger_adapter: logging.LoggerAdapter, config: dict):
    """
    This method is run per process. Each process will connect to service bus and try to establish a session.
    If messages are there, the process will continue to receive all the messages associated with that session.
    If no messages are there, the session connection will time out, sleep, and retry.
    """
    q_name = config["resource_request_queue"]

    while True:
        try:
            logger_adapter.info("Looking for new session...")
            # max_wait_time=1 -> don't hold the session open after processing of the message has finished
            async with service_bus_client.get_queue_receiver(queue_name=q_name, max_wait_time=1, session_id=NEXT_AVAILABLE_SESSION) as receiver:
                logger_adapter.info("Got a session containing messages")
                async with AutoLockRenewer() as renewer:
                    # allow a session to be auto lock renewed for up to an hour - if it's processing a message
                    renewer.register(receiver, receiver.session, max_lock_renewal_duration=3600)

                    async for msg in receiver:
                        result = True
                        message = ""

                        try:
                            message = json.loads(str(msg))
                            logger_adapter.info(f"Message received for resource_id={message['id']}, operation_id={message['operationId']}, step_id={message['stepId']}")
                            message_logger_adapter = get_message_id_logger(message['operationId'])  # correlate messages per operation
                            result = await invoke_porter_action(message, service_bus_client, message_logger_adapter, config)
                        except (json.JSONDecodeError) as e:
                            logging.error(f"Received bad service bus resource request message: {e}")

                        if result:
                            logging.info(f"Resource request for {message} is complete")
                        else:
                            logging.error('Message processing failed!')

                        logger_adapter.info(f"Message for resource_id={message['id']}, operation_id={message['operationId']} processed as {result} and marked complete.")
                        await receiver.complete_message(msg)

                    logger_adapter.info("Closing session")
                    await renewer.close()

        except OperationTimeoutError:
            # Timeout occurred whilst connecting to a session - this is expected and indicates no non-empty sessions are available
            logger_adapter.info("No sessions for this process. Will look again...")

        except ServiceBusConnectionError:
            # Occasionally there will be a transient / network-level error in connecting to SB.
            logger_adapter.info("Unknown Service Bus connection error. Will retry...")

        except Exception:
            # Catch all other exceptions, log them via .exception to get the stack trace, sleep, and reconnect
            logger_adapter.exception("Unknown exception. Will retry...")


async def run_porter(command, logger_adapter: logging.LoggerAdapter, config: dict):
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


def service_bus_message_generator(sb_message: dict, status: str, deployment_message: str, outputs=None):
    """
    Generate a resource request message
    """
    installation_id = get_installation_id(sb_message)
    message_dict = {
        "operationId": sb_message["operationId"],
        "stepId": sb_message["stepId"],
        "id": sb_message["id"],
        "status": status,
        "message": f"{installation_id}: {deployment_message}"}

    if outputs is not None:
        message_dict["outputs"] = outputs

    resource_request_message = json.dumps(message_dict)
    return resource_request_message


async def invoke_porter_action(msg_body: dict, sb_client: ServiceBusClient, message_logger_adapter: logging.LoggerAdapter, config: dict) -> bool:
    """
    Handle resource message by invoking specified porter action (i.e. install, uninstall)
    """
    installation_id = get_installation_id(msg_body)
    action = msg_body["action"]
    message_logger_adapter.info(f"{installation_id}: {action} action starting...")
    sb_sender = sb_client.get_queue_sender(queue_name=config["deployment_status_queue"])

    # post an update message to set the status to an 'in progress' one
    resource_request_message = service_bus_message_generator(msg_body, statuses.in_progress_status_string_for[action], "Job starting")
    await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"]))

    # Build and run porter command (flagging if its a built-in action or custom so we can adapt porter command appropriately)
    is_custom_action = action not in ["install", "upgrade", "uninstall"]
    porter_command = await build_porter_command(config, message_logger_adapter, msg_body, is_custom_action)
    message_logger_adapter.debug("Starting to run porter execution command...")
    returncode, _, err = await run_porter(porter_command, message_logger_adapter, config)
    message_logger_adapter.debug("Finished running porter execution command.")

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
        _, outputs = await get_porter_outputs(msg_body, message_logger_adapter, config)

        success_message = f"{action} action completed successfully."
        resource_request_message = service_bus_message_generator(msg_body, statuses.pass_status_string_for[action], success_message, outputs)

        await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"]))
        message_logger_adapter.info(f"{installation_id}: {success_message}")
        return True


async def get_porter_outputs(msg_body: dict, message_logger_adapter: logging.LoggerAdapter, config: dict):
    """
    Get outputs JSON from a Porter command
    """
    porter_command = await build_porter_command_for_outputs(msg_body)
    message_logger_adapter.debug("Starting to run porter output command...")
    returncode, stdout, err = await run_porter(porter_command, message_logger_adapter, config)
    message_logger_adapter.debug("Finished running porter output command.")

    if returncode != 0:
        error_message = "Error context message = " + " ".join(err.split('\n'))
        message_logger_adapter.info(f"{get_installation_id(msg_body)}: Failed to get outputs with error = {error_message}")
        return False, ""
    else:
        outputs_json = {}
        try:
            outputs_json = json.loads(stdout)

            # loop props individually to try to deserialise to dict/list, as all TF outputs are strings, but we want the pure value
            for i in range(0, len(outputs_json)):
                if "{" in outputs_json[i]['Value'] or "[" in outputs_json[i]['Value']:
                    outputs_json[i]['Value'] = json.loads(outputs_json[i]['Value'].replace("\\", ""))

            message_logger_adapter.info(f"Got outputs as json: {outputs_json}")
        except ValueError:
            message_logger_adapter.error(f"Got outputs invalid json: {stdout}")

        return True, outputs_json


async def runner(logger_adapter: logging.LoggerAdapter, config: dict):
    async with default_credentials(config["vmss_msi_id"]) as credential:
        service_bus_client = ServiceBusClient(config["service_bus_namespace"], credential)
        await receive_message(service_bus_client, logger_adapter, config)


def start_runner_process(config: dict):
    # Set up logger adapter copy for this process
    logger_adapter = set_up_logger(enable_console_logging=False)
    asyncio.run(runner(logger_adapter, config))


async def check_runners(processes: list, httpserver: Process, logger_adapter: logging.LoggerAdapter):
    logger_adapter.info("Starting runners check...")

    while True:
        await asyncio.sleep(30)

        if all(not process.is_alive() for process in processes):
            logger_adapter.error("All runner processes have failed!")
            httpserver.kill()


if __name__ == "__main__":
    logger_adapter: logging.LoggerAdapter = set_up_logger(enable_console_logging=True)
    config = set_up_config(logger_adapter)

    httpserver = Process(target=start_server)
    httpserver.start()
    logger_adapter.info("Started http server")

    processes = []
    num = config["number_processes_int"]
    logger_adapter.info(f"Starting {num} processes...")
    for i in range(num):
        logger_adapter.info(f"Starting process {str(i)}")
        process = Process(target=lambda: start_runner_process(config))
        processes.append(process)
        process.start()

    logger_adapter.info("All proceesses have been started. Version is: %s", VERSION)

    asyncio.run(check_runners(processes, httpserver, logger_adapter))

    logger_adapter.warn("Exiting main...")
