import logging
import click
from tre.api_client import ApiClient


@click.command(name="api", help="Call an API endpoint")
@click.option("--url",
              required=True,
              help="The API URL to call, e.g. /api/workspaces")
@click.option("--scope",
              required=False,
              help="The login scope for the API call")
def call_api(url, scope):
    log = logging.getLogger(__name__)
    client = ApiClient.get_api_client_from_config()
    response = client.call_api(log, url, scope)
    click.echo(response.text + '\n')
