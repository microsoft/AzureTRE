import json
import logging
import click

from tre.api_client import ApiClient
from tre.commands.operation import operation_show
from tre.commands.workspaces.workspace_services.contexts import WorkspaceServiceContext, pass_workspace_service_context
from tre.output import output, output_option, query_option


@click.group(name="user-resources", help="List/add user user resources ")
def user_resources():
    pass


@click.command(name="list", help="List user resources")
@output_option()
@query_option()
@pass_workspace_service_context
def user_resources_list(workspace_service_context: WorkspaceServiceContext, output_format, query):
    log = logging.getLogger(__name__)

    workspace_id = workspace_service_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')
    workspace_service_id = workspace_service_context.workspace_service_id
    if workspace_service_id is None:
        raise click.UsageError('Missing workspace service ID')

    client = ApiClient.get_api_client_from_config()

    workspace_scope = client.get_workspace_scope(log, workspace_id)

    response = client.call_api(
        log,
        'GET',
        f'/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}/user-resources',
        scope_id=workspace_scope,
    )
    output(response, output_format=output_format, query=query, default_table_query=r"userResources[].{id:id, template_name:templateName, template_version:templateVersion, display_name:properties.display_name, owner:user.name}")


@click.command(name="new", help="Create a new user resource")
@click.option('--definition', help='JSON definition for the user resource', required=False)
@click.option('--definition-file', help='File containing JSON definition for the user resource', required=False, type=click.File("r"))
@click.option('--no-wait',
              flag_value=True,
              default=False)
@output_option()
@query_option()
@pass_workspace_service_context
def user_resouce_create(workspace_service_context: WorkspaceServiceContext, definition, definition_file, no_wait, output_format, query):
    log = logging.getLogger(__name__)

    workspace_id = workspace_service_context.workspace_id
    if workspace_id is None:
        raise click.UsageError('Missing workspace ID')
    workspace_service_id = workspace_service_context.workspace_service_id
    if workspace_service_id is None:
        raise click.UsageError('Missing workspace service ID')

    if definition is None:
        if definition_file is None:
            raise click.UsageError('Please specify either a definition or a definition file')
        definition = definition_file.read()

    definition_dict = json.loads(definition)

    client = ApiClient.get_api_client_from_config()
    workspace_scope = client.get_workspace_scope(log, workspace_id)
    click.echo("Creating user-resource...", err=True)
    response = client.call_api(
        log,
        'POST',
        f'/api/workspaces/{workspace_id}/workspace-services/{workspace_service_id}/user-resources',
        json_data=definition_dict,
        scope_id=workspace_scope
    )

    if no_wait:
        output(response, output_format=output_format, query=query)
        return response.text
    else:
        operation_url = response.headers['location']
        operation_show(log, operation_url, no_wait=False, output_format=output_format, query=query, scope_id=workspace_scope)


user_resources.add_command(user_resources_list)
user_resources.add_command(user_resouce_create)
