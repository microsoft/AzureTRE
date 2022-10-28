import json
import logging
import click

from tre.api_client import ApiClient
from tre.output import output, output_option, query_option

from tre.commands.workspace_service_templates.contexts import pass_workspace_service_template_context, WorkspaceServiceTemplateContext


@click.group(name="user-resource-templates", help="List user-resource-templates ")
def user_resource_templates():
    pass


@click.command(name="list", help="List user-resource-templates")
@output_option()
@query_option()
@pass_workspace_service_template_context
def user_resource_templates_list(workspace_service_template_context: WorkspaceServiceTemplateContext, output_format, query):
    log = logging.getLogger(__name__)

    client = ApiClient.get_api_client_from_config()

    template_name = workspace_service_template_context.template_name
    if template_name is None:
        raise click.UsageError('Missing workspace service name')

    response = client.call_api(
        log,
        'GET',
        f'/api/workspace-service-templates/{template_name}/user-resource-templates',
    )
    output(response, output_format=output_format, query=query, default_table_query=r"templates[].{name:name, title: title, description:description}")


@click.command(name="new", help="Register a new user resource template")
@click.option('--definition', help='JSON definition for the template', required=False)
@click.option('--definition-file', help='File containing JSON definition for the template', required=False, type=click.File("r"))
@output_option()
@query_option()
@pass_workspace_service_template_context
def user_resource_templates_create(workspace_service_template_context: WorkspaceServiceTemplateContext, definition, definition_file, output_format, query):
    log = logging.getLogger(__name__)

    if definition is None:
        if definition_file is None:
            raise click.UsageError('Please specify either a definition or a definition file')
        definition = definition_file.read()

    template_name = workspace_service_template_context.template_name
    if template_name is None:
        raise click.UsageError('Missing workspace service name')

    definition_dict = json.loads(definition)

    client = ApiClient.get_api_client_from_config()
    click.echo("Registering template...", err=True)
    response = client.call_api(
        log,
        'POST',
        f'/api/workspace-service-templates/{template_name}/user-resource-templates',
        json_data=definition_dict
    )

    output(response, output_format=output_format, query=query, default_table_query=r"{id: id, name:name, title: title, description:description}")
    return response.text


user_resource_templates.add_command(user_resource_templates_list)
user_resource_templates.add_command(user_resource_templates_create)
