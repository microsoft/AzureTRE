import click
import logging

from tre.api_client import ApiClient
from tre.output import output, output_option, query_option


@click.command(name="health", help="Show Health")
@output_option()
@query_option()
def health(output_format, query) -> None:
    log = logging.getLogger(__name__)

    client = ApiClient.get_api_client_from_config()
    response = client.call_api(log, 'GET', '/api/health')
    output(
        response,
        output_format=output_format,
        query=query,
        default_table_query="services")
    return response.text
