import sys
import click
import logging

from tre.api_client import ApiClient
from tre.output import output, output_option, query_option


@click.command(name="migrations", help="Run migrations")
@output_option()
@query_option()
def migrations(output_format, query) -> None:
    log = logging.getLogger(__name__)

    client = ApiClient.get_api_client_from_config()
    response = client.call_api(log, 'POST', '/api/migrations')
    output(
        response,
        output_format=output_format,
        query=query,
        default_table_query="migrations")

    if not response.is_success:
        sys.exit(1)
