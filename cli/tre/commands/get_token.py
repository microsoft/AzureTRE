import json
import click
import logging
import jwt

from tre.api_client import ApiClient
from tre.commands.workspaces.workspace import workspace_id_completion
from tre.output import output_result, output_option, query_option


@click.command(name="get-token", help="Get an access token")
@click.option('--scope',
              required=False,
              help='The scope to get the token for (defaults to root scope)')
@click.option('--workspace',
              required=False,
              help='The workspace to the token for (cannot be used with --scope)',
              shell_complete=workspace_id_completion)
@click.option('--decode',
              is_flag=True,
              help='Decode the JWT token')
@output_option()
@query_option()
def get_token(scope, workspace, decode, output_format, query):
    log = logging.getLogger(__name__)

    client = ApiClient.get_api_client_from_config()

    if workspace is not None:
        if scope is not None:
            raise click.ClickException("Cannot use --scope and --workspace")
        else:
            scope = client.get_workspace_scope(log, workspace)

    token = client.get_auth_token(log, scope)
    if decode:
        # Skip signature verification otherwise we get:
        # 'Could not deserialize key data. The data may be in an incorrect format, it may be encrypted with an
        # unsupported algorithm, or it may be an unsupported key type (e.g. EC curves with explicit parameters).'
        click.echo("Warning: the signature of the token is not verified", err=True)
        decoded_token = jwt.decode(token, algorithms=['RS256'], options={"verify_signature": False})
        output_result(json.dumps(decoded_token), output_format=output_format, query=query)
    else:
        if output_format:
            click.echo("Ignoring --output for non-decoded token", err=True)
        if query:
            click.echo("Ignoring --query for non-decoded token", err=True)
        click.echo(token)
