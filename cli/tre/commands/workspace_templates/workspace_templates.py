import logging
import click

from tre.api_client import ApiClient
from tre.output import output, output_option, query_option


@click.group(name="workspace-templates", help="List workspace-templates ")
def workspace_templates():
    pass


@click.command(name="list", help="List workspace-templates")
@output_option()
@query_option()
def workspace_templates_list(output_format, query):
    log = logging.getLogger(__name__)

    client = ApiClient.get_api_client_from_config()

    response = client.call_api(
        log,
        'GET',
        '/api/workspace-templates',
    )
    output(response.text, output_format=output_format, query=query, default_table_query=r"templates[].{name:name, title: title, description:description}")


workspace_templates.add_command(workspace_templates_list)
