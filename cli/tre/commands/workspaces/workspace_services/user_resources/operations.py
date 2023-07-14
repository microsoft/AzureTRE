import logging
import click
from tre.api_client import ApiClient
from tre.commands.operation import operations_list
from tre.output import output_option, query_option

from .contexts import UserResourceContext, pass_user_resource_context


@click.group(name="operations", help="List operations ")
def user_resource_operations():
    pass


@click.command(name="list", help="List user resource operations")
@output_option()
@query_option()
@pass_user_resource_context
def user_resource_operations_list(user_resource_operation_context: UserResourceContext, output_format, query):
    log = logging.getLogger(__name__)

    workspace_id = user_resource_operation_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')
    workspace_service_id = user_resource_operation_context.workspace_service_id
    if workspace_service_id is None:
        raise click.UsageError('Missing workspace-service ID')
    user_resource_id = user_resource_operation_context.user_resource_id
    if user_resource_id is None:
        raise click.UsageError('Missing user-resource ID')
    operations_url = f'/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}/user-resources/{user_resource_id}/operations'
    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)
    operations_list(log, operations_url, output_format, query, scope_id=workspace_scope)


user_resource_operations.add_command(user_resource_operations_list)
