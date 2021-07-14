import asyncio
import json
import logging
import os
import socket
import subprocess
import sys


sys.path.append(os.path.realpath('../'))
from shared.logger import initialize_logging  # pylint: disable=import-error # noqa
from shared.service_bus import ServiceBus  # pylint: disable=import-error # noqa
from resources import strings # pylint: disable=import-error # noqa


registry_server = os.environ["REGISTRY_SERVER"]
arm_tenant_id = os.environ['ARM_TENANT_ID']
arm_subscription_id = os.environ['ARM_SUBSCRIPTION_ID']
resource_processor_client_id = os.environ['RESOURCE_PROCESSOR_CLIENT_ID']
resource_processor_client_secret = os.environ['RESOURCE_PROCESSOR_CLIENT_SECRET']
tfstate_container_name = os.environ['TERRAFORM_STATE_CONTAINER_NAME']
tfstate_resource_group_name = os.environ['MGMT_RESOURCE_GROUP_NAME']
tfstate_storage_account_name = os.environ['MGMT_STORAGE_ACCOUNT_NAME']

if os.environ.keys().__contains__("LOCAL_DEV"):
    local_dev = os.environ['LOCAL_DEV']
else:
    local_dev = False


async def main():

    logger_adapter = initialize_logging(logging.INFO, socket.gethostname())

    if local_dev:
        az_login_command = f"az login --service-principal -u {resource_processor_client_id} -p '{resource_processor_client_secret}' --tenant {arm_tenant_id}"
    else:
        az_login_command = "az login --identity"

    service_bus = ServiceBus()

    while True:
        logger_adapter.info("Waiting for messages\n")
        msg = service_bus.get_resource_job_queue_message()

        message_logger_adapter = initialize_logging(logging.INFO, msg.correlation_id)
        message_logger_adapter.info("Processing message\n")

        try:
            msg_body = json.loads(str(msg))

            installation_id = msg_body['parameters']['tre_id'] + "-" + msg_body['parameters']['workspace_id']
            message_logger_adapter.info(f"{installation_id}: Deployment job configuration starting")
            service_bus.send_status_update_message(msg.correlation_id, strings.RESOURCE_STATUS_DEPLOYING, f"{installation_id}: Deployment job configuration starting")

            env_vars = {}
            env_vars["HOME"] = os.environ['HOME']
            env_vars["PATH"] = os.environ['PATH']
            env_vars["ARM_CLIENT_ID"] = resource_processor_client_id
            env_vars["ARM_CLIENT_SECRET"] = resource_processor_client_secret
            env_vars["ARM_SUBSCRIPTION_ID"] = arm_subscription_id
            env_vars["ARM_TENANT_ID"] = arm_tenant_id
            env_vars["PORTER_DRIVER"] = "docker"

            porter_parameters = ""
            for parameter in msg_body['parameters']:
                porter_parameters = porter_parameters + f" --param {parameter}={msg_body['parameters'][parameter]}"

            porter_parameters = porter_parameters + f" --param tfstate_container_name={tfstate_container_name}"
            porter_parameters = porter_parameters + f" --param tfstate_resource_group_name={tfstate_resource_group_name}"
            porter_parameters = porter_parameters + f" --param tfstate_storage_account_name={tfstate_storage_account_name}"

            command_line = ["/bin/bash", "-c", f"{az_login_command} && az acr login --name {registry_server} && porter "
                            f"{msg_body['action']} {installation_id} "
                            f" --reference {registry_server}/{msg_body['name']}:v{msg_body['version']}"
                            f" {porter_parameters} --cred ./azure.json --allow-docker-host-access"
                            f" && porter show {installation_id}"]

            message_logger_adapter.info(f"{installation_id}: Deployment job starting")
            service_bus.send_status_update_message(msg.correlation_id, strings.RESOURCE_STATUS_DEPLOYING, f"{installation_id}: Deployment job starting")
            process = subprocess.Popen(command_line, env=env_vars, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            full_output = ""
            while True:
                output = process.stdout.readline()
                if output == b'' and process.poll() is not None:
                    break
                if output:
                    full_output = full_output + output.decode("utf-8")
                    message_logger_adapter.debug(output.decode('utf8'))
            
            # TODO: this needs encoding in some way as breaks service bus message format
            last_20_lines = full_output.split("\n")[-20:]
            message_logger_adapter.info(f"{installation_id}: Deployment job complete: {last_20_lines}")

            if process.returncode != 0:
                service_bus.send_status_update_message(msg.correlation_id, strings.RESOURCE_STATUS_FAILED, last_20_lines)
            else:
                service_bus.send_status_update_message(msg.correlation_id, strings.RESOURCE_STATUS_DEPLOYED, last_20_lines)
                            

        except Exception as e:
            message_logger_adapter.error("Error occurred during deployment job")
            message_logger_adapter.error(e)
            service_bus.send_status_update_message(msg.correlation_id, strings.RESOURCE_STATUS_FAILED, str(e))

        finally:
            try:
                service_bus.complete_resource_job_queue_message(msg)
            except Exception as e:
                message_logger_adapter.error("Error occurred during message completion")
                message_logger_adapter.error(e)
                service_bus.send_status_update_message(msg.correlation_id, strings.RESOURCE_STATUS_FAILED, str(e))

if __name__ == '__main__':
    asyncio.run(main())
