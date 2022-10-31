import json
import click
import logging

from tre.api_client import ApiClient
from tre.commands.operation import operation_show
from tre.output import output, output_option, query_option
from .contexts import pass_shared_service_context, SharedServiceContext

from .operation import shared_service_operation
from .operations import shared_service_operations


def shared_service_id_completion(ctx: click.Context, param: click.Parameter, incomplete: str):
    log = logging.getLogger(__name__)
    client = ApiClient.get_api_client_from_config()
    response = client.call_api(log, 'GET', '/api/shared-services')
    if response.is_success:
        ids = [shared_service["id"] for shared_service in response.json()["sharedServices"]]
        return [id for id in ids if id.startswith(incomplete)]


@click.group(invoke_without_command=True, help="Perform actions on an individual shared_service")
@click.argument('shared_service_id', required=True, type=click.UUID, shell_complete=shared_service_id_completion)
@click.pass_context
def shared_service(ctx: click.Context, shared_service_id: str) -> None:
    ctx.obj = SharedServiceContext(shared_service_id)


@click.command(name="show", help="Show a shared_service")
@output_option()
@query_option()
@pass_shared_service_context
def shared_service_show(shared_service_context: SharedServiceContext, output_format, query):
    log = logging.getLogger(__name__)

    shared_service_id = shared_service_context.shared_service_id
    if shared_service_id is None:
        raise click.UsageError('Missing shared_service ID')

    client = ApiClient.get_api_client_from_config()
    response = client.call_api(log, 'GET', f'/api/shared-services/{shared_service_id}', )
    output(response, output_format=output_format, query=query, default_table_query=r"sharedService.{id:id,name:templateName, version:templateVersion, is_enabled:isEnabled, status: deploymentStatus}")


@click.command(name="invoke-action", help="Invoke an action on a shared_service")
@click.argument('action-name', required=True)
@click.option('--no-wait',
              flag_value=True,
              default=False)
@output_option()
@query_option()
@click.pass_context
@pass_shared_service_context
def shared_service_invoke_action(shared_service_context: SharedServiceContext, ctx: click.Context, action_name, no_wait, output_format, query):
    log = logging.getLogger(__name__)

    shared_service_id = shared_service_context.shared_service_id
    if shared_service_id is None:
        raise click.UsageError('Missing shared_service ID')

    client = ApiClient.get_api_client_from_config()
    click.echo(f"Invoking action {action_name}...\n", err=True)
    response = client.call_api(
        log,
        'POST',
        f'/api/shared-services/{shared_service_id}/invoke-action?action={action_name}'
    )
    if no_wait:
        output(response, output_format=output_format, query=query)
    else:
        operation_url = response.headers['location']
        operation_show(log, operation_url, no_wait=False, output_format=output_format, query=query)


@click.command(name="update", help="Update a shared service")
@click.option('--etag',
              help='The etag of the shared service to update',
              required=True)
@click.option('--definition', help='JSON definition for the shared service', required=False)
@click.option('--definition-file', help='File containing JSON definition for the workspace', required=False, type=click.File("r"))
@click.option('--no-wait',
              flag_value=True,
              default=False)
@output_option()
@query_option()
@click.pass_context
@pass_shared_service_context
def shared_service_update(shared_service_context: SharedServiceContext, ctx: click.Context, etag, definition, definition_file, no_wait, output_format, query, suppress_output: bool = False):
    log = logging.getLogger(__name__)

    shared_service_id = shared_service_context.shared_service_id
    if shared_service_id is None:
        raise click.UsageError('Missing shared_service ID')

    if definition is None:
        if definition_file is None:
            raise click.UsageError('Please specify either a definition or a definition file')
        definition = definition_file.read()

    definition_dict = json.loads(definition)

    client = ApiClient.get_api_client_from_config()
    response = client.call_api(
        log,
        'PATCH',
        f'/api/shared-services/{shared_service_id}',
        headers={'etag': etag},
        json_data=definition_dict)

    if no_wait:
        output(response, output_format=output_format, query=query, default_table_query=r"sharedService.{id:id,name:templateName, version:templateVersion, is_enabled:isEnabled, status: deploymentStatus}")
    else:
        operation_url = response.headers['location']
        operation_show(log, operation_url, no_wait=False, output_format=output_format, query=query, suppress_output=suppress_output)


@click.command(name="set-enabled", help="Enable/disable a shared service")
@click.option('--etag',
              help='The etag of the shared service to update',
              required=True)
@click.option('--enable/--disable', is_flag=True, required=True)
@click.option('--no-wait',
              flag_value=True,
              default=False)
@output_option()
@query_option()
@pass_shared_service_context
def shared_service_set_enabled(shared_service_context: SharedServiceContext, etag, enable, no_wait, output_format, query, suppress_output: bool = False):
    log = logging.getLogger(__name__)

    shared_service_id = shared_service_context.shared_service_id
    if shared_service_id is None:
        raise click.UsageError('Missing shared_service ID')

    client = ApiClient.get_api_client_from_config()
    click.echo(f"Setting isEnabled to {enable}...", err=True)
    response = client.call_api(
        log,
        'PATCH',
        f'/api/shared-services/{shared_service_id}',
        headers={'etag': etag},
        json_data={'isEnabled': enable})

    if no_wait:
        if not suppress_output or not response.is_success:
            output(response, output_format=output_format, query=query, default_table_query=r"sharedService.{id:id,name:templateName, version:templateVersion, is_enabled:isEnabled, status: deploymentStatus}")
    else:
        operation_url = response.headers['location']
        operation_show(log, operation_url, no_wait=False, output_format=output_format, query=query, suppress_output=suppress_output)


@click.command(name="delete", help="Delete a shared_service")
@click.option('--yes', is_flag=True, default=False)
@click.option('--no-wait',
              flag_value=True,
              default=False)
@click.option('--ensure-disabled',
              help="Ensure disabled before deleting (resources are required to be disabled before deleting)",
              flag_value=True,
              default=False)
@click.pass_context
@output_option()
@query_option()
@pass_shared_service_context
def shared_service_delete(shared_service_context: SharedServiceContext, ctx: click.Context, yes, no_wait, ensure_disabled, output_format, query):
    log = logging.getLogger(__name__)

    shared_service_id = shared_service_context.shared_service_id
    if shared_service_id is None:
        raise click.UsageError('Missing shared_service ID')

    if not yes:
        click.confirm("Are you sure you want to delete this shared_service?", err=True, abort=True)

    client = ApiClient.get_api_client_from_config()

    if ensure_disabled:
        response = client.call_api(log, 'GET', f'/api/shared-services/{shared_service_id}')
        shared_service_json = response.json()
        if shared_service_json['sharedService']['isEnabled']:
            etag = shared_service_json['sharedService']['_etag']
            ctx.invoke(
                shared_service_set_enabled,
                etag=etag,
                enable=False,
                no_wait=False,
                suppress_output=True
            )

    click.echo("Deleting shared_service...\n", err=True)
    response = client.call_api(log, 'DELETE', f'/api/shared-services/{shared_service_id}')
    if no_wait:
        output(response, output_format=output_format, query=query)
    else:
        operation_url = response.headers['location']
        operation_show(log, operation_url, no_wait=False, output_format=output_format, query=query)


shared_service.add_command(shared_service_show)
shared_service.add_command(shared_service_invoke_action)
shared_service.add_command(shared_service_update)
shared_service.add_command(shared_service_set_enabled)
shared_service.add_command(shared_service_delete)
shared_service.add_command(shared_service_operations)
shared_service.add_command(shared_service_operation)
