import click
import logging

from tre.api_client import ApiClient


@click.command(name="get-token", help="Get an access token")
@click.option('--scope',
              required=False,
              help='The scope to get the token for (defaults to root scope)')
@click.option('--workspace',
              required=False,
              help='The workspace to the token for (cannot be used with --scope)')
def get_token(scope, workspace):
    log = logging.getLogger(__name__)

    client = ApiClient.get_api_client_from_config()

    if workspace is not None:
        if scope is not None:
            raise click.ClickException("Cannot use --scope and --workspace")
        else:
            scope = client.get_workspace_scope(log, workspace)

    token = client.get_auth_token(log, scope)
    click.echo(token)
