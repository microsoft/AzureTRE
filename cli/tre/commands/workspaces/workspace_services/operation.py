import logging
import click
from tre.commands.operation import get_operation_id_completion, operation_show
from tre.output import output_option, query_option
from tre.api_client import ApiClient

from .contexts import pass_workspace_service_operation_context, WorkspaceServiceOperationContext


def operation_id_completion(ctx: click.Context, param: click.Parameter, incomplete: str):
    log = logging.getLogger(__name__)
    parent_ctx = ctx.parent
    workspace_service_id = parent_ctx.params["workspace_service_id"]
    parent2_ctx = parent_ctx.parent
    workspace_id = parent2_ctx.params["workspace_id"]
    list_url = f'/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}/operations'

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    return get_operation_id_completion(ctx, log, list_url, param, incomplete, scope_id=workspace_scope)


@click.group(name="operation", invoke_without_command=True, help="Perform actions on an operation")
@click.argument('operation_id', required=True, type=click.UUID, shell_complete=operation_id_completion)
@click.pass_context
def workspace_service_operation(ctx: click.Context, operation_id) -> None:
    ctx.obj = WorkspaceServiceOperationContext.add_operation_id_to_context_obj(ctx, operation_id)


@click.command(name="show", help="Workspace-service operation")
@click.option('--no-wait',
              help="If an operation is in progress, do not wait for it to complete",
              flag_value=True,
              default=False)
@output_option()
@query_option()
@pass_workspace_service_operation_context
def workspace_service_operation_show(workspace_service_operation_context: WorkspaceServiceOperationContext, no_wait, output_format, query, suppress_output: bool = False) -> None:
    log = logging.getLogger(__name__)

    workspace_id = workspace_service_operation_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')
    workspace_service_id = workspace_service_operation_context.workspace_service_id
    if workspace_service_id is None:
        raise click.UsageError('Missing workspace-service ID')
    operation_id = workspace_service_operation_context.operation_id
    if operation_id is None:
        raise click.UsageError('Missing operation ID')

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    operation_url = f'/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}/operations/{operation_id}'
    operation_show(log, operation_url, no_wait, output_format, query, suppress_output, scope_id=workspace_scope)


workspace_service_operation.add_command(workspace_service_operation_show)
