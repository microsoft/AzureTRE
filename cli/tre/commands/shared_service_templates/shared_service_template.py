import logging
import click
from tre.api_client import ApiClient
from tre.output import output, output_option, query_option

from .contexts import SharedServiceTemplateContext, pass_shared_service_template_context


def template_name_completion(ctx: click.Context, param: click.Parameter, incomplete: str):
    log = logging.getLogger(__name__)
    client = ApiClient.get_api_client_from_config()
    response = client.call_api(log, 'GET', '/api/shared-service-templates')
    if response.is_success:
        names = [workspace["name"] for workspace in response.json()["templates"]]
        return [name for name in names if name.startswith(incomplete)]


@click.group(name="shared-service-template", invoke_without_command=True, help="Perform actions on an shared-service-template")
@click.argument('template_name', required=True, shell_complete=template_name_completion)
@click.pass_context
def shared_service_template(ctx: click.Context, template_name) -> None:
    ctx.obj = SharedServiceTemplateContext(template_name)


@click.command(name="show", help="Show template")
@output_option()
@query_option()
@pass_shared_service_template_context
def shared_service_template_show(shared_service_template_context: SharedServiceTemplateContext, output_format, query) -> None:
    log = logging.getLogger(__name__)

    template_name = shared_service_template_context.template_name
    if template_name is None:
        raise click.UsageError('Missing template name')

    client = ApiClient.get_api_client_from_config()

    response = client.call_api(
        log,
        'GET',
        f'/api/shared-service-templates/{template_name}',
    )

    output(response, output_format=output_format, query=query, default_table_query=r"{id: id, name:name, title: title, version:version, description:description}")


shared_service_template.add_command(shared_service_template_show)
