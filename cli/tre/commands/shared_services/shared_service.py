import click
import logging

from tre.api_client import ApiClient
from tre.commands.operation import operation_show
from tre.output import output, output_option, query_option
from .contexts import pass_shared_service_context, SharedServiceContext

from .operation import shared_service_operation
from .operations import shared_service_operations


@click.group(invoke_without_command=True, help="Perform actions on an individual shared_service")
@click.argument('shared_service_id', required=True, type=click.UUID)
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
    output(response.text, output_format=output_format, query=query, default_table_query=r"sharedServices[].{id:id,name:templateName, version:templateVersion, is_enabled:isEnabled, status: deploymentStatus}")

#
# TODO - add PATCH (and ?set-enabled)
#

# TODO - invoke action


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
        output(response.text, output_format=output_format, query=query)
    else:
        operation_url = response.headers['location']
        operation_show(log, operation_url, no_wait=False, output_format=output_format, query=query)


@click.command(name="delete", help="Delete a shared_service")
@click.option('--yes', is_flag=True, default=False)
@click.option('--no-wait',
              flag_value=True,
              default=False)
@click.pass_context
@output_option()
@query_option()
@pass_shared_service_context
def shared_service_delete(shared_service_context: SharedServiceContext, ctx: click.Context, yes, no_wait, output_format, query):
    log = logging.getLogger(__name__)

    shared_service_id = shared_service_context.shared_service_id
    if shared_service_id is None:
        raise click.UsageError('Missing shared_service ID')

    if not yes:
        click.confirm("Are you sure you want to delete this shared_service?", err=True, abort=True)

    client = ApiClient.get_api_client_from_config()
    click.echo("Deleting shared_service...\n", err=True)
    response = client.call_api(log, 'DELETE', f'/api/shared-services/{shared_service_id}')
    if no_wait:
        output(response.text, output_format=output_format, query=query)
    else:
        operation_url = response.headers['location']
        operation_show(log, operation_url, no_wait=False, output_format=output_format, query=query)


shared_service.add_command(shared_service_show)
shared_service.add_command(shared_service_invoke_action)
shared_service.add_command(shared_service_delete)
shared_service.add_command(shared_service_operations)
shared_service.add_command(shared_service_operation)
