import logging
import click
from tre.api_client import ApiClient
from tre.output import output, output_option, query_option

from .contexts import WorkspaceServiceTemplateContext, pass_workspace_service_template_context

from .user_resource_templates.user_resource_templates import user_resource_templates
from .user_resource_templates.user_resource_template import user_resource_template


def template_name_completion(ctx: click.Context, param: click.Parameter, incomplete: str):
    log = logging.getLogger(__name__)
    client = ApiClient.get_api_client_from_config()
    response = client.call_api(log, 'GET', '/api/workspace-service-templates')
    if response.is_success:
        names = [workspace["name"] for workspace in response.json()["templates"]]
        return [name for name in names if name.startswith(incomplete)]


@click.group(name="workspace-service-template", invoke_without_command=True, help="Perform actions on an workspace-service-template")
@click.argument('template_name', required=True, shell_complete=template_name_completion)
@click.pass_context
def workspace_service_template(ctx: click.Context, template_name) -> None:
    ctx.obj = WorkspaceServiceTemplateContext(template_name)


@click.command(name="show", help="Show template")
@output_option()
@query_option()
@pass_workspace_service_template_context
def workspace_service_template_show(workspace_service_template_context: WorkspaceServiceTemplateContext, output_format, query) -> None:
    log = logging.getLogger(__name__)

    template_name = workspace_service_template_context.template_name
    if template_name is None:
        raise click.UsageError('Missing template name')

    client = ApiClient.get_api_client_from_config()

    response = client.call_api(
        log,
        'GET',
        f'/api/workspace-service-templates/{template_name}',
    )

    output(response, output_format=output_format, query=query, default_table_query=r"{id: id, name:name, title: title, version:version, description:description}")


workspace_service_template.add_command(workspace_service_template_show)
workspace_service_template.add_command(user_resource_template)
workspace_service_template.add_command(user_resource_templates)
