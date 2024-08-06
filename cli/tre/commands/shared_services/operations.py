import logging
import click
from tre.commands.operation import operations_list
from tre.output import output_option, query_option

from .contexts import SharedServiceContext, pass_shared_service_context


@click.group(name="operations", help="List operations ")
def shared_service_operations():
    pass


@click.command(name="list", help="List shared_service operations")
@output_option()
@query_option()
@pass_shared_service_context
def shared_service_operations_list(shared_service_context: SharedServiceContext, output_format, query):
    log = logging.getLogger(__name__)

    shared_service_id = shared_service_context.shared_service_id
    if shared_service_id is None:
        raise click.UsageError('Missing shared_service ID')

    operations_url = f'/api/shared-services/{shared_service_id}/operations'
    operations_list(log, operations_url, output_format, query)


shared_service_operations.add_command(shared_service_operations_list)
