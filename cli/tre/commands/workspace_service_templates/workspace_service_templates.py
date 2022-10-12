import logging
import click

from tre.api_client import ApiClient
from tre.output import output, output_option, query_option


@click.group(name="workspace-service-templates", help="List workspace-service-templates ")
def workspace_service_templates():
    pass


@click.command(name="list", help="List workspace-service-templates")
@output_option()
@query_option()
def workspace_service_templates_list(output_format, query):
    log = logging.getLogger(__name__)

    client = ApiClient.get_api_client_from_config()

    response = client.call_api(
        log,
        'GET',
        '/api/workspace-service-templates',
    )
    output(response.text, output_format=output_format, query=query, default_table_query=r"templates[].{name:name, title: title, description:description}")


workspace_service_templates.add_command(workspace_service_templates_list)
