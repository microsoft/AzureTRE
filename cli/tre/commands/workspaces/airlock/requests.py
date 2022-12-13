import click
import logging

from tre.api_client import ApiClient
from tre.commands.workspaces.contexts import pass_workspace_context
from tre.output import output, output_option, query_option

_default_table_query_list = r"airlockRequests[].airlockRequest.{id:id,workspace_id:workspaceId,type:type,status:status,business_justification:businessJustification}"
_default_table_query_item = r"airlockRequest.{id:id,workspace_id:workspaceId,type:type,status:status,business_justification:businessJustification}"


@click.group(name="airlock-requests", help="List/add airlock requests")
def airlocks() -> None:
    pass


@click.command(name="list", help="List airlocks")
@output_option()
@query_option()
@pass_workspace_context
def airlocks_list(workspace_context, output_format, query):
    log = logging.getLogger(__name__)

    workspace_id = workspace_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    response = client.call_api(
        log,
        'GET',
        f'/api/workspaces/{workspace_id}/requests',
        scope_id=workspace_scope,
    )
    output(response, output_format=output_format, query=query, default_table_query=_default_table_query_list)


@click.command(name="new", help="Create a new airlock request")
@click.option('--type', "request_type", help='The type of request', required=True, type=click.Choice(['import', 'export']))
@click.option('--title', help='Title for the request', required=True)
@click.option('--justification', help='Business justification for the request', required=True)
@output_option()
@query_option()
@pass_workspace_context
def airlock_create(workspace_context, request_type, title, justification, output_format, query):
    log = logging.getLogger(__name__)

    workspace_id = workspace_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    click.echo("Creating airlock request...", err=True)
    response = client.call_api(
        log,
        'POST',
        f'/api/workspaces/{workspace_id}/requests',
        json_data={
            "type": request_type,
            "title": title,
            "businessJustification": justification
        },
        scope_id=workspace_scope)

    output(response, output_format=output_format, query=query, default_table_query=_default_table_query_item)
    return response.text


airlocks.add_command(airlocks_list)
airlocks.add_command(airlock_create)
