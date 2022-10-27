import logging
import click
from tre.api_client import ApiClient
from tre.output import output, output_option, query_option

from .contexts import UserResourceTemplateContext, pass_user_resource_template_context


def template_name_completion(ctx: click.Context, param: click.Parameter, incomplete: str):
    log = logging.getLogger(__name__)
    parent_ctx = ctx.parent
    workspace_service_name = parent_ctx.params["template_name"]
    client = ApiClient.get_api_client_from_config()
    response = client.call_api(log, 'GET', f'/api/workspace-service-templates/{workspace_service_name}/user-resource-templates')
    if response.is_success:
        names = [template["name"] for template in response.json()["templates"]]
        return [name for name in names if name.startswith(incomplete)]


@click.group(name="user-resource-template", invoke_without_command=True, help="Perform actions on an user-resource-template")
@click.argument('template_name', required=True, shell_complete=template_name_completion)
@click.pass_context
def user_resource_template(ctx: click.Context, template_name) -> None:
    ctx.obj = UserResourceTemplateContext.add_template_name_to_context_obj(ctx, template_name)


@click.command(name="show", help="Show template")
@output_option()
@query_option()
@pass_user_resource_template_context
def user_resource_template_show(user_resource_template_context: UserResourceTemplateContext, output_format, query) -> None:
    log = logging.getLogger(__name__)

    workspace_service_name = user_resource_template_context.workspace_service_name
    if workspace_service_name is None:
        raise click.UsageError('Missing workspace service name')
    template_name = user_resource_template_context.template_name
    if template_name is None:
        raise click.UsageError('Missing template name')

    client = ApiClient.get_api_client_from_config()

    response = client.call_api(
        log,
        'GET',
        f'/api/workspace-service-templates/{workspace_service_name}/user-resource-templates/{template_name}',
    )

    output(response, output_format=output_format, query=query, default_table_query=r"{id: id, name:name, title: title, version:version, description:description}")


user_resource_template.add_command(user_resource_template_show)
