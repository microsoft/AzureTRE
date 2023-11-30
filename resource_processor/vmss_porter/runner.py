from typing import Optional
from multiprocessing import Process
import json
import asyncio
import logging
import sys
from resources.commands import azure_acr_login_command, azure_login_command, build_porter_command, build_porter_command_for_outputs, apply_porter_credentials_sets_command
from shared.config import get_config
from resources.helpers import get_installation_id
from resources.httpserver import start_server

from shared.logging import initialize_logging, logger, shell_output_logger, tracer
from shared.config import VERSION
from resources import statuses
from contextlib import asynccontextmanager
from azure.servicebus import ServiceBusMessage, NEXT_AVAILABLE_SESSION
from azure.servicebus.exceptions import OperationTimeoutError, ServiceBusConnectionError
from azure.servicebus.aio import ServiceBusClient, AutoLockRenewer
from azure.identity.aio import DefaultAzureCredential


def set_up_config() -> Optional[dict]:
    try:
        config = get_config()
        return config
    except KeyError as e:
        logger.error(f"Environment variable {e} is not set correctly...Exiting")
        sys.exit(1)


@asynccontextmanager
async def default_credentials(msi_id):
    """
    Context manager which yields the default credentials.
    """
    credential = DefaultAzureCredential(managed_identity_client_id=msi_id) if msi_id else DefaultAzureCredential()
    yield credential
    await credential.close()


async def receive_message(service_bus_client, config: dict):
    """
    This method is run per process. Each process will connect to service bus and try to establish a session.
    If messages are there, the process will continue to receive all the messages associated with that session.
    If no messages are there, the session connection will time out, sleep, and retry.
    """
    q_name = config["resource_request_queue"]

    while True:
        try:
            logger.info("Looking for new session...")
            # max_wait_time=1 -> don't hold the session open after processing of the message has finished
            async with service_bus_client.get_queue_receiver(queue_name=q_name, max_wait_time=1, session_id=NEXT_AVAILABLE_SESSION) as receiver:
                logger.info(f"Got a session containing messages: {receiver.session.session_id}")
                async with AutoLockRenewer() as renewer:
                    # allow a session to be auto lock renewed for up to an hour - if it's processing a message
                    renewer.register(receiver, receiver.session, max_lock_renewal_duration=3600)

                    async for msg in receiver:
                        result = True
                        message = ""

                        try:
                            message = json.loads(str(msg))
                        except (json.JSONDecodeError) as e:
                            logger.error(f"Received bad service bus resource request message: {e}")

                        with tracer.start_as_current_span("receive_message") as current_span:
                            current_span.set_attribute("resource_id", message["id"])
                            current_span.set_attribute("action", message["action"])
                            current_span.set_attribute("step_id", message["stepId"])
                            current_span.set_attribute("operation_id", message["operationId"])
                            logger.info(f"Message received for resource_id={message['id']}, operation_id={message['operationId']}, step_id={message['stepId']}")

                            result = await invoke_porter_action(message, service_bus_client, config)

                            if result:
                                logger.info(f"Resource request for {message} is complete")
                            else:
                                logger.error('Message processing failed!')

                            logger.info(f"Message for resource_id={message['id']}, operation_id={message['operationId']} processed as {result} and marked complete.")
                            await receiver.complete_message(msg)

                    logger.info(f"Closing session: {receiver.session.session_id}")

        except OperationTimeoutError:
            # Timeout occurred whilst connecting to a session - this is expected and indicates no non-empty sessions are available
            logger.debug("No sessions for this process. Will look again...")

        except ServiceBusConnectionError:
            # Occasionally there will be a transient / network-level error in connecting to SB.
            logger.info("Unknown Service Bus connection error. Will retry...")

        except Exception:
            # Catch all other exceptions, log them via .exception to get the stack trace, sleep, and reconnect
            logger.exception("Unknown exception. Will retry...")


async def run_porter(command, config: dict):
    """
    Run a Porter command
    """
    command = [
        f"{azure_login_command(config)} && ",
        f"{azure_acr_login_command(config)} && ",
        f"{apply_porter_credentials_sets_command(config)} && ",
        *command
    ]

    proc = await asyncio.create_subprocess_shell(''.join(command),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=config["porter_env"])

    stdout, stderr = await proc.communicate()
    logger.debug(f'run porter exited with {proc.returncode}')
    result_stdout = None
    result_stderr = None

    if stdout:
        result_stdout = stdout.decode()
        shell_output_logger(result_stdout, '[stdout]', logging.INFO)

    if stderr:
        result_stderr = stderr.decode()
        shell_output_logger(result_stderr, '[stderr]', logging.WARN)

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
    logger.debug(f"Deployment Status Message: {resource_request_message}")
    return resource_request_message


async def invoke_porter_action(msg_body: dict, sb_client: ServiceBusClient, config: dict) -> bool:
    """
    Handle resource message by invoking specified porter action (i.e. install, uninstall)
    """

    installation_id = get_installation_id(msg_body)
    action = msg_body["action"]
    logger.info(f"{action} action starting for {installation_id}...")
    sb_sender = sb_client.get_queue_sender(queue_name=config["deployment_status_queue"])

    # post an update message to set the status to an 'in progress' one
    resource_request_message = service_bus_message_generator(msg_body, statuses.in_progress_status_string_for[action], "Job starting")
    await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"], session_id=msg_body["operationId"]))
    logger.info(f'Sent status message for {installation_id} - {statuses.in_progress_status_string_for[action]} - Job starting')

    # Build and run porter command (flagging if its a built-in action or custom so we can adapt porter command appropriately)
    is_custom_action = action not in ["install", "upgrade", "uninstall"]
    porter_command = await build_porter_command(config, msg_body, is_custom_action)

    logger.debug("Starting to run porter execution command...")
    returncode, _, err = await run_porter(porter_command, config)
    logger.debug("Finished running porter execution command.")
    action_completed_without_error = True

    # Handle command output
    if returncode != 0 and err is not None:
        error_message = "Error message: " + " ".join(err.split('\n')) + "; Command executed: " + " ".join(porter_command)
        action_completed_without_error = False

        if "uninstall" == action and "could not find installation" in err:
            logger.warning("The installation doesn't exist. Treating as a successful action to allow the flow to proceed.")
            action_completed_without_error = True
            error_message = f"A success despite of underlying error. {error_message}"

        if action_completed_without_error:
            status_for_sb_message = statuses.pass_status_string_for[action]
        else:
            status_for_sb_message = statuses.failed_status_string_for[action]

        resource_request_message = service_bus_message_generator(msg_body, status_for_sb_message, error_message)

        # Post message on sb queue to notify receivers of action failure
        logger.info(f"{installation_id}: Porter action failed with error = {error_message}")

    else:
        # Get the outputs
        get_porter_outputs_successful, outputs = await get_porter_outputs(msg_body, config)

        if get_porter_outputs_successful:
            status_for_sb_message = statuses.pass_status_string_for[action]
            status_message = f"{action} action completed successfully."
        else:
            action_completed_without_error = False
            status_for_sb_message = statuses.failed_status_string_for[action]
            status_message = f"{action} action completed successfully, but failed to get outputs."

        resource_request_message = service_bus_message_generator(msg_body, status_for_sb_message, status_message, outputs)

    await sb_sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=msg_body["id"], session_id=msg_body["operationId"]))
    logger.info(f"Sent status message for {installation_id}: {status_for_sb_message}")

    # return true as want to continue processing the message
    return action_completed_without_error


async def get_porter_outputs(msg_body: dict, config: dict):
    """
    Get outputs JSON from a Porter command
    """
    porter_command = await build_porter_command_for_outputs(msg_body)
    logger.debug("Starting to run porter output command...")
    returncode, stdout, err = await run_porter(porter_command, config)
    logger.debug("Finished running porter output command.")

    if returncode != 0:
        error_message = "Error context message = " + " ".join(err.split('\n'))
        logger.info(f"{get_installation_id(msg_body)}: Failed to get outputs with error = {error_message}")
        return False, {}
    else:
        outputs_json = {}
        try:
            outputs_json = json.loads(stdout)

            # loop props individually to try to deserialise to dict/list, as all TF outputs are strings, but we want the pure value
            for i in range(0, len(outputs_json)):
                if "{" in outputs_json[i]['value'] or "[" in outputs_json[i]['value']:
                    outputs_json[i]['value'] = json.loads(outputs_json[i]['value'].replace("\\", ""))

            logger.info(f"Got outputs as json: {outputs_json}")
        except ValueError:
            logger.error(f"Got outputs invalid json: {stdout}")

        return True, outputs_json


async def runner(process_number: int, config: dict):
    with tracer.start_as_current_span(process_number):
        async with default_credentials(config["vmss_msi_id"]) as credential:
            service_bus_client = ServiceBusClient(config["service_bus_namespace"], credential)
            await receive_message(service_bus_client, config)


async def check_runners(processes: list, httpserver: Process):
    logger.info("Starting runners check...")

    while True:
        await asyncio.sleep(30)
        if all(not process.is_alive() for process in processes):
            logger.error("All runner processes have failed!")
            httpserver.kill()


if __name__ == "__main__":
    initialize_logging()
    logger.info("Resource processor starting...")
    with tracer.start_as_current_span("resource_processor_main"):
        config = set_up_config()

        logger.info("Verifying Azure CLI and Porter functionality...")
        asyncio.run(run_porter(["az account show -o table"], config))

        httpserver = Process(target=start_server)
        httpserver.start()
        logger.info("Started http server")

        processes = []
        num = config["number_processes_int"]
        logger.info(f"Starting {num} processes...")
        for i in range(num):
            logger.info(f"Starting process {str(i)}")
            process = Process(target=lambda: asyncio.run(runner(i, config)))
            processes.append(process)
            process.start()

        logger.info("All processes have been started. Version is: %s", VERSION)

        asyncio.run(check_runners(processes, httpserver))

        logger.warn("Exiting main...")
