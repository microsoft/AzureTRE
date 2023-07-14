import logging
import click
from tre.commands.operation import operations_list
from tre.output import output_option, query_option

from .contexts import WorkspaceContext, pass_workspace_context


@click.group(name="operations", help="List operations ")
def workspace_operations():
    pass


@click.command(name="list", help="List workspace operations")
@output_option()
@query_option()
@pass_workspace_context
def workspace_operations_list(workspace_context: WorkspaceContext, output_format, query):
    log = logging.getLogger(__name__)

    workspace_id = workspace_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')
    operations_url = f'/api/workspaces/{workspace_id}/operations'
    operations_list(log, operations_url, output_format, query)


workspace_operations.add_command(workspace_operations_list)
