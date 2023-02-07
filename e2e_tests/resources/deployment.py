import logging
import backoff
from httpx import TimeoutException
from e2e_tests.helpers import get_full_endpoint
from e2e_tests.resources import strings

LOGGER = logging.getLogger(__name__)


async def delete_done(client, operation_endpoint, headers):
    delete_terminal_states = [strings.RESOURCE_STATUS_DELETED, strings.RESOURCE_STATUS_DELETING_FAILED]
    deployment_status, message, operation_steps = await check_deployment(client, operation_endpoint, headers)
    return (True, deployment_status, message, operation_steps) if deployment_status in delete_terminal_states else (False, deployment_status, message, operation_steps)


async def install_done(client, operation_endpoint, headers):
    install_terminal_states = [strings.RESOURCE_STATUS_DEPLOYED, strings.RESOURCE_STATUS_DEPLOYMENT_FAILED]
    deployment_status, message, operation_steps = await check_deployment(client, operation_endpoint, headers)
    return (True, deployment_status, message, operation_steps) if deployment_status in install_terminal_states else (False, deployment_status, message, operation_steps)


async def patch_done(client, operation_endpoint, headers):
    install_terminal_states = [strings.RESOURCE_STATUS_UPDATED, strings.RESOURCE_STATUS_UPDATING_FAILED]
    deployment_status, message, operation_steps = await check_deployment(client, operation_endpoint, headers)
    return (True, deployment_status, message, operation_steps) if deployment_status in install_terminal_states else (False, deployment_status, message, operation_steps)


@backoff.on_exception(backoff.constant,
                      TimeoutException,  # catching all timeout types (Connection, Read, etc.)
                      max_time=90)
async def check_deployment(client, operation_endpoint, headers):
    full_endpoint = get_full_endpoint(operation_endpoint)

    response = await client.get(full_endpoint, headers=headers, timeout=5.0)
    if response.status_code == 200:
        response_json = response.json()
        deployment_status = response_json["operation"]["status"]
        message = response_json["operation"]["message"]
        operation_steps = stringify_operation_steps(response_json["operation"]["steps"])
        return deployment_status, message, operation_steps
    else:
        LOGGER.error(f"Non 200 response in check_deployment: {response.status_code}")
        LOGGER.error(f"Full response: {response}")
        raise Exception("Non 200 response in check_deployment")


def stringify_operation_steps(steps):
    string = ''
    for i, step in enumerate(steps, 1):
        string += f'Step {i}: {step["stepTitle"]}\n'
        string += f'{step["message"]}\n\n'
    return string
