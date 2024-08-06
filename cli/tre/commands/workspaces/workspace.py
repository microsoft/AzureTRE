import json
import sys
import click
import logging

from tre.api_client import ApiClient
from tre.commands.operation import default_operation_table_query_single, operation_show
from tre.output import output, output_option, query_option
from .contexts import pass_workspace_context, WorkspaceContext

from .operation import workspace_operation
from .operations import workspace_operations
from .workspace_services.workspace_service import workspace_service
from .workspace_services.workspace_services import workspace_services
from .airlock.requests import airlocks
from .airlock.request import airlock


def workspace_id_completion(ctx: click.Context, param: click.Parameter, incomplete: str):
    log = logging.getLogger(__name__)
    client = ApiClient.get_api_client_from_config()
    response = client.call_api(log, 'GET', '/api/workspaces')
    if response.is_success:
        ids = [workspace["id"] for workspace in response.json()["workspaces"]]
        return [id for id in ids if id.startswith(incomplete)]


@click.group(invoke_without_command=True, help="Perform actions on an individual workspace")
@click.argument('workspace_id', envvar='TRECLI_WORKSPACE_ID', type=click.UUID, required=True, shell_complete=workspace_id_completion)
@click.pass_context
def workspace(ctx: click.Context, workspace_id: str) -> None:
    ctx.obj = WorkspaceContext(workspace_id)


@click.command(name="show", help="Show a workspace")
@output_option()
@query_option()
@pass_workspace_context
def workspace_show(workspace_context: WorkspaceContext, output_format, query):
    log = logging.getLogger(__name__)

    workspace_id = workspace_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')

    client = ApiClient.get_api_client_from_config()
    response = client.call_api(log, 'GET', f'/api/workspaces/{workspace_id}', )

    output(
        response,
        output_format=output_format,
        query=query,
        default_table_query=r"workspace.{id:id, display_name:properties.display_name, deployment_status:deploymentStatus, workspace_url:workspaceURL}")
    return response.text


@click.command(name="update", help="Update a workspace")
@click.option('--etag',
              help='The etag of the workspace to update',
              required=True)
@click.option('--definition', help='JSON definition for the workspace', required=False)
@click.option('--definition-file', help='File containing JSON definition for the workspace', required=False, type=click.File("r"))
@click.option('--no-wait',
              flag_value=True,
              default=False)
@output_option()
@query_option()
@click.pass_context
@pass_workspace_context
def workspace_update(workspace_context: WorkspaceContext, ctx: click.Context, etag, definition, definition_file, no_wait, output_format, query, suppress_output: bool = False):
    log = logging.getLogger(__name__)

    workspace_id = workspace_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')

    if definition is None:
        if definition_file is None:
            raise click.UsageError('Please specify either a definition or a definition file')
        definition = definition_file.read()

    definition_dict = json.loads(definition)

    client = ApiClient.get_api_client_from_config()
    response = client.call_api(
        log,
        'PATCH',
        f'/api/workspaces/{workspace_id}',
        headers={'etag': etag},
        json_data=definition_dict)

    if no_wait:
        output(response, output_format=output_format, query=query, default_table_query=default_operation_table_query_single())
        if not response.is_success:
            sys.exit(1)
    else:
        operation_url = response.headers['location']
        operation_show(log, operation_url, no_wait=False, output_format=output_format, query=query, suppress_output=suppress_output)


@click.command(name="set-enabled", help="Enable/disable a workspace")
@click.option('--etag',
              help='The etag of the workspace to update',
              required=True)
@click.option('--enable/--disable', is_flag=True, required=True)
@click.option('--no-wait',
              flag_value=True,
              default=False)
@output_option()
@query_option()
@pass_workspace_context
def workspace_set_enabled(workspace_context: WorkspaceContext, etag, enable, no_wait, output_format, query, suppress_output: bool = False):
    log = logging.getLogger(__name__)

    workspace_id = workspace_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')

    client = ApiClient.get_api_client_from_config()
    click.echo(f"Setting isEnabled to {enable}...", err=True)
    response = client.call_api(
        log,
        'PATCH',
        f'/api/workspaces/{workspace_id}',
        headers={'etag': etag},
        json_data={'isEnabled': enable})

    if no_wait:
        if not suppress_output or not response.is_success:
            output(response, output_format=output_format, query=query, default_table_query=default_operation_table_query_single())
    else:
        operation_url = response.headers['location']
        operation_show(log, operation_url, no_wait=False, output_format=output_format, query=query, suppress_output=suppress_output)


@click.command(name="delete", help="Delete a workspace")
@click.option('--yes', is_flag=True, default=False)
@click.option('--no-wait',
              flag_value=True,
              default=False)
@click.option('--ensure-disabled',
              help="Ensure disabled before deleting (resources are required to be disabled before deleting)",
              flag_value=True,
              default=False)
@output_option()
@query_option()
@click.pass_context
@pass_workspace_context
def workspace_delete(workspace_context: WorkspaceContext, ctx: click.Context, yes, no_wait, ensure_disabled, output_format, query):
    log = logging.getLogger(__name__)

    workspace_id = workspace_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')

    if not yes:
        click.confirm("Are you sure you want to delete this workspace?", err=True, abort=True)

    client = ApiClient.get_api_client_from_config()

    if ensure_disabled:
        response = client.call_api(log, 'GET', f'/api/workspaces/{workspace_id}')
        workspace_json = response.json()
        if workspace_json['workspace']['isEnabled']:
            etag = workspace_json['workspace']['_etag']
            ctx.invoke(
                workspace_set_enabled,
                etag=etag,
                enable=False,
                no_wait=False,
                suppress_output=True
            )

    click.echo("Deleting workspace...", err=True)
    response = client.call_api(log, 'DELETE', f'/api/workspaces/{workspace_id}')

    if no_wait:
        output(response, output_format=output_format, query=query, default_table_query=default_operation_table_query_single())
        if not response.is_success:
            sys.exit(1)
    else:
        operation_url = response.headers['location']
        operation_show(log, operation_url, no_wait, output_format=output_format, query=query)


@click.command(name="invoke-action", help="Invoke an action on a workspace")
@click.argument("action-name", required=True)
@click.option("--no-wait", flag_value=True, default=False)
@output_option()
@query_option()
@pass_workspace_context
def workspace_service_invoke_action(
    workspace_context: WorkspaceContext,
    action_name,
    no_wait,
    output_format,
    query,
):
    log = logging.getLogger(__name__)

    workspace_id = workspace_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')

    client = ApiClient.get_api_client_from_config()

    click.echo(f"Invoking action {action_name}...\n", err=True)
    response = client.call_api(
        log,
        "POST",
        f"/api/workspaces/{workspace_id}/invoke-action",
        params={"action": action_name},
    )
    if no_wait:
        output(response, output_format=output_format, query=query)
        if not response.is_success:
            sys.exit(1)
    else:
        operation_url = response.headers["location"]
        operation_show(
            log,
            operation_url,
            no_wait=False,
            output_format=output_format,
            query=query,
        )


workspace.add_command(workspace_show)
workspace.add_command(workspace_update)
workspace.add_command(workspace_set_enabled)
workspace.add_command(workspace_delete)
workspace.add_command(workspace_operations)
workspace.add_command(workspace_operation)

workspace.add_command(workspace_services)
workspace.add_command(workspace_service)

workspace.add_command(airlock)
workspace.add_command(airlocks)
