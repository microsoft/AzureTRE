import click
import logging

from tre.api_client import ApiClient
from tre.commands.workspaces.airlock.contexts import WorkspaceAirlockContext, pass_workspace_airlock_context
from tre.output import output, output_option, query_option

_default_table_query_item = r"airlockRequest.{id:id,workspace_id:workspaceId,type:type, title:title,status:status,business_justification:businessJustification}"


def airlock_id_completion(ctx: click.Context, param: click.Parameter, incomplete: str):
    log = logging.getLogger(__name__)
    parent_ctx = ctx.parent
    workspace_id = parent_ctx.params["workspace_id"]
    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)
    response = client.call_api(log, 'GET', f'/api/workspaces/{workspace_id}/requests', scope_id=workspace_scope)
    if response.is_success:
        ids = [request["airlockRequest"]["id"] for request in response.json()["airlockRequests"]]
        return [id for id in ids if id.startswith(incomplete)]


@click.group(name="airlock-request", invoke_without_command=True, help="Perform actions on an airlock request")
@click.argument('airlock_id', required=True, type=click.UUID, shell_complete=airlock_id_completion)
@click.pass_context
def airlock(ctx: click.Context, airlock_id: str) -> None:
    ctx.obj = WorkspaceAirlockContext.add_airlock_id_to_context_obj(ctx, airlock_id)


@click.command(name="show", help="Show airlock request")
@output_option()
@query_option()
@pass_workspace_airlock_context
def airlock_show(airlock_context: WorkspaceAirlockContext, output_format, query) -> None:
    log = logging.getLogger(__name__)

    workspace_id = airlock_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')
    airlock_id = airlock_context.airlock_id
    if airlock_id is None:
        raise click.UsageError('Missing airlock request ID')

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    response = client.call_api(
        log,
        'GET',
        f'/api/workspaces/{workspace_id}/requests/{airlock_id}',
        scope_id=workspace_scope,
    )

    output(response, output_format=output_format, query=query, default_table_query=_default_table_query_item)


@click.command(name="get-url", help="Get URL to access airlock request")
@output_option()
@query_option()
@pass_workspace_airlock_context
def airlock_get_url(airlock_context: WorkspaceAirlockContext, output_format, query) -> None:
    log = logging.getLogger(__name__)

    workspace_id = airlock_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')
    airlock_id = airlock_context.airlock_id
    if airlock_id is None:
        raise click.UsageError('Missing service ID')

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    response = client.call_api(
        log,
        'GET',
        f'/api/workspaces/{workspace_id}/requests/{airlock_id}/link',
        scope_id=workspace_scope,
    )

    output(response, output_format=output_format, query=query, default_table_query=r"{container_url:containerUrl}")


@click.command(name="submit", help="Submit an airlock request (after uploading content)")
@output_option()
@query_option()
@pass_workspace_airlock_context
def airlock_submit(airlock_context: WorkspaceAirlockContext, output_format, query) -> None:
    log = logging.getLogger(__name__)

    workspace_id = airlock_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')
    airlock_id = airlock_context.airlock_id
    if airlock_id is None:
        raise click.UsageError('Missing airlock request ID')

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    response = client.call_api(
        log,
        'POST',
        f'/api/workspaces/{workspace_id}/requests/{airlock_id}/submit',
        scope_id=workspace_scope,
    )

    output(
        response,
        output_format=output_format,
        query=query,
        default_table_query=_default_table_query_item)


@click.command(name="review", help="Provide a review response for an airlock request")
@click.option('--approve/--reject', 'approve', required=True, help="Approved/rejected")
@click.option('--reason', required=True, help="Reason for approval/rejection")
@output_option()
@query_option()
@pass_workspace_airlock_context
def airlock_review(airlock_context: WorkspaceAirlockContext, approve, reason, output_format, query) -> None:
    log = logging.getLogger(__name__)

    workspace_id = airlock_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')
    airlock_id = airlock_context.airlock_id
    if airlock_id is None:
        raise click.UsageError('Missing airlock request ID')

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    response = client.call_api(
        log,
        'POST',
        f'/api/workspaces/{workspace_id}/requests/{airlock_id}/review',
        json_data={
            "approval": approve,
            "decisionExplanation": reason,
        },
        scope_id=workspace_scope,
    )

    output(
        response,
        output_format=output_format,
        query=query,
        default_table_query=_default_table_query_item)


@click.command(name="cancel", help="Cancel an airlock request")
@output_option()
@query_option()
@pass_workspace_airlock_context
def airlock_cancel(airlock_context: WorkspaceAirlockContext, output_format, query) -> None:
    log = logging.getLogger(__name__)

    workspace_id = airlock_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')
    airlock_id = airlock_context.airlock_id
    if airlock_id is None:
        raise click.UsageError('Missing airlock request ID')

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    response = client.call_api(
        log,
        'POST',
        f'/api/workspaces/{workspace_id}/requests/{airlock_id}/cancel',
        scope_id=workspace_scope,
    )

    output(
        response,
        output_format=output_format,
        query=query,
        default_table_query=_default_table_query_item)


airlock.add_command(airlock_show)
airlock.add_command(airlock_get_url)
airlock.add_command(airlock_submit)
airlock.add_command(airlock_review)
airlock.add_command(airlock_cancel)
