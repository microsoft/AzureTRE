import json
import logging
import click
from tre.api_client import ApiClient
from tre.commands.operation import default_operation_table_query_single, operation_show
from tre.output import output, output_option, query_option

from .contexts import WorkspaceServiceContext, pass_workspace_service_context
from .operation import workspace_service_operation
from .operations import workspace_service_operations
from .user_resources.user_resource import user_resource
from .user_resources.user_resources import user_resources


def workspace_service_id_completion(ctx: click.Context, param, incomplete):
    log = logging.getLogger(__name__)
    parent_ctx = ctx.parent
    workspace_id = parent_ctx.params["workspace_id"]
    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)
    response = client.call_api(log, 'GET', f'/api/workspaces/{workspace_id}/workspace-services', scope_id=workspace_scope)
    if response.is_success:
        ids = [workspace["id"] for workspace in response.json()["workspaceServices"]]
        return [id for id in ids if id.startswith(incomplete)]


@click.group(name="workspace-service", invoke_without_command=True, help="Perform actions on an workspace-service")
@click.argument('workspace_service_id', required=True, type=click.UUID, shell_complete=workspace_service_id_completion)
@click.pass_context
def workspace_service(ctx: click.Context, workspace_service_id) -> None:
    ctx.obj = WorkspaceServiceContext.add_service_id_to_context_obj(ctx, workspace_service_id)


@click.command(name="show", help="Workspace service")
@output_option()
@query_option()
@pass_workspace_service_context
def workspace_service_show(workspace_service_context: WorkspaceServiceContext, output_format, query) -> None:
    log = logging.getLogger(__name__)

    workspace_id = workspace_service_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')
    workspace_service_id = workspace_service_context.workspace_service_id
    if workspace_service_id is None:
        raise click.UsageError('Missing service ID')

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    response = client.call_api(
        log,
        'GET',
        f'/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}',
        scope_id=workspace_scope,
    )

    output(response.text, output_format=output_format, query=query, default_table_query=r"workspaceService.{id:id,template_name:templateName,template_version:templateVersion,sdeployment_status:deploymentStatus}")


@click.command(name="update", help="Update a workspace service")
@click.option('--etag',
              help='The etag of the workspace service to update',
              required=True)
@click.option('--definition', help='JSON definition for the workspace service', required=False)
@click.option('--definition-file', help='File containing JSON definition for the workspace service', required=False, type=click.File("r"))
@click.option('--no-wait',
              flag_value=True,
              default=False)
@output_option()
@query_option()
@pass_workspace_service_context
def workspace_service_update(workspace_service_context: WorkspaceServiceContext, etag, definition, definition_file, no_wait, output_format, query, suppress_output: bool = False):
    log = logging.getLogger(__name__)

    workspace_id = workspace_service_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')
    workspace_service_id = workspace_service_context.workspace_service_id
    if workspace_service_id is None:
        raise click.UsageError('Missing service ID')

    if definition is None:
        if definition_file is None:
            raise click.UsageError('Please specify either a definition or a definition file')
        definition = definition_file.read()

    definition_dict = json.loads(definition)

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)
    response = client.call_api(
        log,
        'PATCH',
        f'/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}',
        headers={'etag': etag},
        json_data=definition_dict,
        scope_id=workspace_scope)

    if no_wait:
        output(response.text, output_format=output_format, query=query, default_table_query=default_operation_table_query_single())
    else:
        operation_url = response.headers['location']
        operation_show(
            log,
            operation_url,
            no_wait=False,
            output_format=output_format,
            query=query,
            suppress_output=suppress_output,
            scope_id=workspace_scope)


@click.command(name="set-enabled", help="Enable/disable a workspace service")
@click.option('--etag',
              help='The etag of the workspace service to update',
              required=True)
@click.option('--enable/--disable', is_flag=True, required=True)
@click.option('--no-wait',
              flag_value=True,
              default=False)
@output_option()
@query_option()
@pass_workspace_service_context
def workspace_service_set_enabled(workspace_service_context: WorkspaceServiceContext, etag, enable, no_wait, output_format, query, suppress_output: bool = False):
    log = logging.getLogger(__name__)

    workspace_id = workspace_service_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')
    workspace_service_id = workspace_service_context.workspace_service_id
    if workspace_service_id is None:
        raise click.UsageError('Missing service ID')

    client = ApiClient.get_api_client_from_config()
    click.echo(f"Setting isEnabled to {enable}...", err=True)
    workspace_scope = client.get_workspace_scope(log, workspace_id)
    response = client.call_api(
        log,
        'PATCH',
        f'/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}',
        headers={'etag': etag},
        json_data={'isEnabled': enable},
        scope_id=workspace_scope)

    if no_wait:
        if not suppress_output:
            output(response.text, output_format=output_format, query=query, default_table_query=default_operation_table_query_single())
    else:
        operation_url = response.headers['location']
        operation_show(
            log,
            operation_url,
            no_wait=False,
            output_format=output_format,
            query=query,
            suppress_output=suppress_output,
            scope_id=workspace_scope)


workspace_service.add_command(workspace_service_show)
workspace_service.add_command(workspace_service_update)
workspace_service.add_command(workspace_service_set_enabled)
workspace_service.add_command(workspace_service_operation)
workspace_service.add_command(workspace_service_operations)
workspace_service.add_command(user_resource)
workspace_service.add_command(user_resources)


# TODO delete

# TODO - invoke action
