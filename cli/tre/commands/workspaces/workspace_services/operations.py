import logging
import click
from tre.api_client import ApiClient
from tre.commands.operation import operations_list
from tre.output import output_option, query_option

from .contexts import WorkspaceServiceContext, pass_workspace_service_context


@click.group(name="operations", help="List operations ")
def workspace_service_operations():
    pass


@click.command(name="list", help="List workspace service operations")
@output_option()
@query_option()
@pass_workspace_service_context
def workspace_service_operations_list(workspace_service_context: WorkspaceServiceContext, output_format, query):
    log = logging.getLogger(__name__)

    workspace_id = workspace_service_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')
    workspace_service_id = workspace_service_context.workspace_service_id
    if workspace_service_id is None:
        raise click.UsageError('Missing workspace-service ID')
    operations_url = f'/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}/operations'
    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)
    operations_list(log, operations_url, output_format, query, scope_id=workspace_scope)


workspace_service_operations.add_command(workspace_service_operations_list)
