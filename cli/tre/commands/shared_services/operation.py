import logging
import click

from tre.commands.operation import get_operation_id_completion, operation_show
from tre.output import output_option, query_option

from .contexts import pass_shared_service_operation_context, SharedServiceOperationContext


def operation_id_completion(ctx: click.Context, param: click.Parameter, incomplete: str):
    log = logging.getLogger(__name__)
    parent_ctx = ctx.parent
    workspace_id = parent_ctx.params["workspace_id"]
    list_url = f'/api/workspaces/{workspace_id}/operations'
    return get_operation_id_completion(ctx, log, list_url, param, incomplete)


@click.group(name="operation", invoke_without_command=True, help="Perform actions on an operation")
@click.argument('operation_id', required=True, type=click.UUID, shell_complete=operation_id_completion)
@click.pass_context
def shared_service_operation(ctx: click.Context, operation_id) -> None:
    ctx.obj = SharedServiceOperationContext.add_operation_id_to_context_obj(ctx, operation_id)


@click.command(name="show", help="SharedService operation")
@click.option('--no-wait',
              help="If an operation is in progress, do not wait for it to complete",
              flag_value=True,
              default=False)
@output_option()
@query_option()
@pass_shared_service_operation_context
def shared_service_operation_show(shared_service_operation_context: SharedServiceOperationContext, no_wait, output_format, query, suppress_output: bool = False):
    log = logging.getLogger(__name__)

    shared_service_id = shared_service_operation_context.shared_service_id
    if shared_service_id is None:
        raise click.UsageError('Missing shared_service ID')
    operation_id = shared_service_operation_context.operation_id
    if operation_id is None:
        raise click.UsageError('Missing operation ID')

    operation_url = f'/api/shared-services/{shared_service_id}/operations/{operation_id}'

    operation_show(log, operation_url, no_wait, suppress_output, output_format=output_format, query=query)


shared_service_operation.add_command(shared_service_operation_show)
