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
    output(response.text, output_format=output_format, query=query, default_table_query=r"templates[].{name:name, title: title, description:description}")


user_resource_templates.add_command(user_resource_templates_list)
