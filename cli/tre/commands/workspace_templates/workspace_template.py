import logging
import click
from tre.api_client import ApiClient
from tre.output import output, output_option, query_option

from .contexts import WorkspaceTemplateContext, pass_workspace_template_context


def template_name_completion(ctx: click.Context, param: click.Parameter, incomplete: str):
    log = logging.getLogger(__name__)
    client = ApiClient.get_api_client_from_config()
    response = client.call_api(log, 'GET', '/api/workspace-templates')
    if response.is_success:
        names = [workspace["name"] for workspace in response.json()["templates"]]
        return [name for name in names if name.startswith(incomplete)]


@click.group(name="workspace-template", invoke_without_command=True, help="Perform actions on an workspace-template")
@click.argument('template_name', required=True, shell_complete=template_name_completion)
@click.pass_context
def workspace_template(ctx: click.Context, template_name) -> None:
    ctx.obj = WorkspaceTemplateContext(template_name)


@click.command(name="show", help="Show template")
@output_option()
@query_option()
@pass_workspace_template_context
def workspace_template_show(workspace_template_context: WorkspaceTemplateContext, output_format, query) -> None:
    log = logging.getLogger(__name__)

    template_name = workspace_template_context.template_name
    if template_name is None:
        raise click.UsageError('Missing template name')

    client = ApiClient.get_api_client_from_config()

    response = client.call_api(
        log,
        'GET',
        f'/api/workspace-templates/{template_name}',
    )

    output(response, output_format=output_format, query=query, default_table_query=r"{id: id, name:name, title: title, version:version, description:description}")


workspace_template.add_command(workspace_template_show)
