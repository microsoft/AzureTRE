import json
import logging
import click
from tre.api_client import ApiClient
from tre.commands.operation import default_operation_table_query_single, operation_show
from tre.output import output, output_option, query_option

from .contexts import UserResourceContext, pass_user_resource_context
from .operation import user_resource_operation
from .operations import user_resource_operations


def user_resource_id_completion(ctx: click.Context, param: click.Parameter, incomplete: str):
    log = logging.getLogger(__name__)
    parent_ctx = ctx.parent
    workspace_service_id = parent_ctx.params["workspace_service_id"]
    parent2_ctx = parent_ctx.parent
    workspace_id = parent2_ctx.params["workspace_id"]

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)
    response = client.call_api(
        log,
        "GET",
        f"/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}/user-resources",
        scope_id=workspace_scope,
    )
    if response.is_success:
        ids = [resource["id"] for resource in response.json()["userResources"]]
        return [id for id in ids if id.startswith(incomplete)]


@click.group(
    name="user-resource",
    invoke_without_command=True,
    help="Perform actions on a user resource",
)
@click.argument(
    "user_resource_id",
    required=True,
    type=click.UUID,
    shell_complete=user_resource_id_completion,
)
@click.pass_context
def user_resource(ctx: click.Context, user_resource_id) -> None:
    ctx.obj = UserResourceContext.add_user_resource_id_to_context_obj(
        ctx, user_resource_id
    )


@click.command(name="show", help="Show user resource")
@output_option()
@query_option()
@pass_user_resource_context
def user_resource_show(
    user_resource_context: UserResourceContext, output_format, query
) -> None:
    log = logging.getLogger(__name__)

    workspace_id = user_resource_context.workspace_id
    if workspace_id is None:
        raise click.UsageError("Missing workspace ID")
    workspace_service_id = user_resource_context.workspace_service_id
    if workspace_service_id is None:
        raise click.UsageError("Missing workspace service ID")
    user_resource_id = user_resource_context.user_resource_id
    if user_resource_id is None:
        raise click.UsageError("Missing user resource ID")

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    response = client.call_api(
        log,
        "GET",
        f"/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}/user-resources/{user_resource_id}",
        scope_id=workspace_scope,
    )

    output(
        response,
        output_format=output_format,
        query=query,
        default_table_query=r"userResource.{id:id, template_name:templateName, template_version:templateVersion, display_name:properties.display_name, owner:user.name}",
    )


@click.command(name="update", help="Update a workspace")
@click.option("--etag", help="The etag of the workspace to update", required=True)
@click.option("--definition", help="JSON definition for the workspace", required=False)
@click.option(
    "--definition-file",
    help="File containing JSON definition for the workspace",
    required=False,
    type=click.File("r"),
)
@click.option("--no-wait", flag_value=True, default=False)
@output_option()
@query_option()
@click.pass_context
@pass_user_resource_context
def user_resource_update(
    user_resource_context: UserResourceContext,
    ctx: click.Context,
    etag,
    definition,
    definition_file,
    no_wait,
    output_format,
    query,
    suppress_output: bool = False,
):
    log = logging.getLogger(__name__)

    workspace_id = user_resource_context.workspace_id
    if workspace_id is None:
        raise click.UsageError("Missing workspace ID")
    workspace_service_id = user_resource_context.workspace_service_id
    if workspace_service_id is None:
        raise click.UsageError("Missing workspace service ID")
    user_resource_id = user_resource_context.user_resource_id
    if user_resource_id is None:
        raise click.UsageError("Missing user resource ID")

    if definition is None:
        if definition_file is None:
            raise click.UsageError(
                "Please specify either a definition or a definition file"
            )
        definition = definition_file.read()

    definition_dict = json.loads(definition)

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    response = client.call_api(
        log,
        "PATCH",
        f"/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}/user-resources/{user_resource_id}",
        headers={"etag": etag},
        json_data=definition_dict,
        scope_id=workspace_scope,
    )

    if no_wait:
        output(
            response,
            output_format=output_format,
            query=query,
            default_table_query=default_operation_table_query_single(),
        )
    else:
        operation_url = response.headers["location"]
        operation_show(
            log,
            operation_url,
            no_wait=False,
            output_format=output_format,
            query=query,
            suppress_output=suppress_output,
            scope_id=workspace_scope,
        )


@click.command(name="set-enabled", help="Enable/disable a user resource")
@click.option("--etag", help="The etag of the user resource to update", required=True)
@click.option("--enable/--disable", is_flag=True, required=True)
@click.option("--no-wait", flag_value=True, default=False)
@output_option()
@query_option()
@pass_user_resource_context
def user_resource_set_enabled(
    user_resource_context: UserResourceContext,
    etag,
    enable,
    no_wait,
    output_format,
    query,
    suppress_output: bool = False,
):
    log = logging.getLogger(__name__)

    workspace_id = user_resource_context.workspace_id
    if workspace_id is None:
        raise click.UsageError("Missing workspace ID")
    workspace_service_id = user_resource_context.workspace_service_id
    if workspace_service_id is None:
        raise click.UsageError("Missing workspace service ID")
    user_resource_id = user_resource_context.user_resource_id
    if user_resource_id is None:
        raise click.UsageError("Missing user resource ID")

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    click.echo(f"Setting isEnabled to {enable}...", err=True)
    response = client.call_api(
        log,
        "PATCH",
        f"/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}/user-resources/{user_resource_id}",
        headers={"etag": etag},
        json_data={"isEnabled": enable},
        scope_id=workspace_scope,
    )

    if no_wait:
        if not suppress_output or not response.is_success:
            output(
                response,
                output_format=output_format,
                query=query,
                default_table_query=default_operation_table_query_single(),
            )
    else:
        operation_url = response.headers["location"]
        operation_show(
            log,
            operation_url,
            no_wait=False,
            output_format=output_format,
            query=query,
            suppress_output=suppress_output,
            scope_id=workspace_scope,
        )


@click.command(name="delete", help="Delete a user resource")
@click.option("--yes", is_flag=True, default=False)
@click.option("--no-wait", flag_value=True, default=False)
@click.option(
    "--ensure-disabled",
    help="Ensure disabled before deleting (resources are required to be disabled before deleting)",
    flag_value=True,
    default=False,
)
@output_option()
@query_option()
@click.pass_context
@pass_user_resource_context
def user_resource_delete(
    user_resource_context: UserResourceContext,
    ctx: click.Context,
    yes,
    no_wait,
    ensure_disabled,
    output_format,
    query,
):
    log = logging.getLogger(__name__)

    workspace_id = user_resource_context.workspace_id
    if workspace_id is None:
        raise click.UsageError("Missing workspace ID")
    workspace_service_id = user_resource_context.workspace_service_id
    if workspace_service_id is None:
        raise click.UsageError("Missing workspace service ID")
    user_resource_id = user_resource_context.user_resource_id
    if user_resource_id is None:
        raise click.UsageError("Missing user resource ID")

    if not yes:
        click.confirm(
            "Are you sure you want to delete this user resource?", err=True, abort=True
        )

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    if ensure_disabled:
        response = client.call_api(
            log,
            "GET",
            f"/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}/user-resources/{user_resource_id}",
            scope_id=workspace_scope,
        )
        workspace_json = response.json()
        if workspace_json["userResource"]["isEnabled"]:
            etag = workspace_json["userResource"]["_etag"]
            ctx.invoke(
                user_resource_set_enabled,
                etag=etag,
                enable=False,
                no_wait=False,
                suppress_output=True,
            )

    click.echo("Deleting user resource...", err=True)
    response = client.call_api(
        log,
        "DELETE",
        f"/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}/user-resources/{user_resource_id}",
        scope_id=workspace_scope,
    )

    if no_wait:
        output(
            response,
            output_format=output_format,
            query=query,
            default_table_query=default_operation_table_query_single(),
        )
    else:
        operation_url = response.headers["location"]
        operation_show(
            log,
            operation_url,
            no_wait,
            output_format=output_format,
            query=query,
            scope_id=workspace_scope,
        )


@click.command(name="invoke-action", help="Invoke an action on a user resource")
@click.argument("action-name", required=True)
@click.option("--no-wait", flag_value=True, default=False)
@output_option()
@query_option()
@pass_user_resource_context
def user_resource_invoke_action(
    user_resource_context: UserResourceContext,
    action_name,
    no_wait,
    output_format,
    query,
):
    log = logging.getLogger(__name__)

    workspace_id = user_resource_context.workspace_id
    if workspace_id is None:
        raise click.UsageError("Missing workspace ID")
    workspace_service_id = user_resource_context.workspace_service_id
    if workspace_service_id is None:
        raise click.UsageError("Missing workspace service ID")
    user_resource_id = user_resource_context.user_resource_id
    if user_resource_id is None:
        raise click.UsageError("Missing user resource ID")

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)

    click.echo(f"Invoking action {action_name}...\n", err=True)
    response = client.call_api(
        log,
        "POST",
        f"/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}/user-resources/{user_resource_id}/invoke-action",
        scope_id=workspace_scope,
        params={"action": action_name},
    )
    if no_wait:
        output(response, output_format=output_format, query=query)
    else:
        operation_url = response.headers["location"]
        operation_show(
            log,
            operation_url,
            no_wait=False,
            output_format=output_format,
            query=query,
            scope_id=workspace_scope,
        )


user_resource.add_command(user_resource_show)
user_resource.add_command(user_resource_update)
user_resource.add_command(user_resource_set_enabled)
user_resource.add_command(user_resource_delete)
user_resource.add_command(user_resource_operation)
user_resource.add_command(user_resource_operations)
user_resource.add_command(user_resource_invoke_action)
