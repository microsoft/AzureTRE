from logging import Logger
import sys
from time import sleep

import click
from tre.api_client import ApiClient
from tre.output import output


def get_operation_id_completion(ctx: click.Context, log: Logger, list_url: str, param: click.Parameter, incomplete: str, scope_id: str = None):
    client = ApiClient.get_api_client_from_config()
    response = client.call_api(log, 'GET', list_url, scope_id=scope_id)
    if response.is_success:
        ids = [workspace["id"] for workspace in response.json()["operations"]]
        return [id for id in ids if id.startswith(incomplete)]


def is_operation_state_terminal(state: str) -> bool:
    # In the absence of a field on the operation indicating whether it is completed or not,
    # we maintain a list here.
    # Note that we test against 'active' states
    # This way, a new state will be considered terminal (and not a success)
    # so we avoid a case where waiting for copmletion continues indefinitely
    # when there is a new state (and we return a non-successful status to
    # highlight it)
    return state not in [
        'deleting',
        'deploying',
        'awaiting_action',
        'invoking_action',
        'pipeline_deploying',
        'pipeline_running',
        'not_deployed',
        'awaiting_deployment',
        'awaiting_deletion',
        'awaiting_update',
        'updating'
    ]


def is_operation_state_success(state: str) -> bool:
    return state in [
        'deleted',
        'deployed',
        'action_succeeded',
        'pipeline_succeeded',
        'updated'
    ]


def default_operation_table_query_list():
    return r"operations[].{id:id, status:status, action:action, resourcePath:resourcePath, message:message}"


def default_operation_table_query_single():
    return r"operation.{id:id, status:status, action:action, resourcePath:resourcePath, message:message}"


def operation_show(log, operation_url, no_wait, output_format, query, suppress_output: bool = False, scope_id: str = None):

    wait_for_completion = not no_wait

    client = ApiClient.get_api_client_from_config()
    response = client.call_api(
        log,
        'GET',
        operation_url,
        scope_id=scope_id
    )
    response_json = response.json()
    action = response_json['operation']['action']
    state = response_json['operation']['status']

    while wait_for_completion and not is_operation_state_terminal(state):
        click.echo(f'Operation state: {state} (action={action})',
                   err=True, nl=False)
        sleep(5)
        click.echo(' - refreshing...', err=True)
        response = client.call_api(
            log,
            'GET',
            operation_url,
            scope_id=scope_id
        )
        response_json = response.json()
        action = response_json['operation']['action']
        state = response_json['operation']['status']

    if not suppress_output or not response.is_success:
        output(response, output_format=output_format, query=query, default_table_query=default_operation_table_query_single())

    if wait_for_completion and not is_operation_state_success(state):
        sys.exit(1)

    return response.text


def operations_list(log, operations_url, output_format, query, scope_id: str = None):
    client = ApiClient.get_api_client_from_config()

    response = client.call_api(
        log,
        'GET',
        operations_url,
        scope_id=scope_id
    )
    output(response, output_format=output_format, query=query, default_table_query=default_operation_table_query_list())
