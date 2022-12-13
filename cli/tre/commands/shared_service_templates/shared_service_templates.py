import json
import logging
import click

from tre.api_client import ApiClient
from tre.output import output, output_option, query_option


@click.group(name="shared-service-templates", help="List shared-service-templates ")
def shared_service_templates():
    pass


@click.command(name="list", help="List shared-service-templates")
@output_option()
@query_option()
def shared_service_templates_list(output_format, query):
    log = logging.getLogger(__name__)

    client = ApiClient.get_api_client_from_config()

    response = client.call_api(
        log,
        'GET',
        '/api/shared-service-templates',
    )
    output(response, output_format=output_format, query=query, default_table_query=r"templates[].{name:name, title: title, description:description}")


@click.command(name="new", help="Register a new shared service template")
@click.option('--definition', help='JSON definition for the template', required=False)
@click.option('--definition-file', help='File containing JSON definition for the template', required=False, type=click.File("r"))
@output_option()
@query_option()
def shared_service_templates_create(definition, definition_file, output_format, query):
    log = logging.getLogger(__name__)

    if definition is None:
        if definition_file is None:
            raise click.UsageError('Please specify either a definition or a definition file')
        definition = definition_file.read()

    definition_dict = json.loads(definition)

    client = ApiClient.get_api_client_from_config()
    click.echo("Registering template...", err=True)
    response = client.call_api(log, 'POST', '/api/shared-service-templates', json_data=definition_dict)

    output(response, output_format=output_format, query=query, default_table_query=r"{id: id, name:name, title: title, description:description}")
    return response.text


shared_service_templates.add_command(shared_service_templates_list)
shared_service_templates.add_command(shared_service_templates_create)
