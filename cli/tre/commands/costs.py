import click
import logging

from tre.api_client import ApiClient
from tre.commands.workspaces.workspace import workspace_id_completion
from tre.output import output, output_option, query_option


@click.group(help="Show costs")
def costs() -> None:
    pass


@click.command(name="overall", help="Show overall costs")
@click.option("--from", "from_date",
              type=click.DateTime(['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y%m%d']),
              help="The start date to pull data from, required if --to is set, otherwise report will return month to date (UTC).")
@click.option("--to", "to_date",
              type=click.DateTime(['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y%m%d']),
              help="The end date to pull data to, required if --to is set, otherwise report will return month to date ( UTC).")
@click.option("--granularity",
              type=click.Choice(["None", "Daily"]),
              required=False,
              help="The granularity of rows in the query.")
@output_option()
@query_option()
def costs_overall(from_date, to_date, granularity, output_format, query):
    log = logging.getLogger(__name__)

    client = ApiClient.get_api_client_from_config()
    url = "/api/costs"
    query_string = ""
    if from_date:
        query_string += f"&from_date={from_date}"
    if to_date:
        query_string += f"&to_date={to_date}"
    if granularity:
        query_string += f"&granularity={granularity}"
    if query_string:
        query_string = query_string[1:]  # drop leading ampersand
        url = url + "?" + query_string

    response = client.call_api(log, 'GET', url)
    output(
        response,
        output_format=output_format,
        # To properly flatten the costs structure for table rendering, we need `let`
        # as per https://jmespath.site/#wiki-lexical-scopes. For now:
        default_table_query="[{category: 'core_services', id: null, name: null, costs: core_services}, shared_services[].{category:'shared_service', id:id, name:name, costs:costs}, workspaces[].{category:'workspace', id:id, name:name, costs:costs}] | []",
        query=query)
    return response.text


@click.command(name="workspace", help="Show costs for a workspace")
@click.argument('workspace_id', envvar='TRECLI_WORKSPACE_ID', type=click.UUID, required=True, shell_complete=workspace_id_completion)
@click.option("--from", "from_date",
              type=click.DateTime(['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y%m%d']),
              help="The start date to pull data from, required if --to is set, otherwise report will return month to date (UTC).")
@click.option("--to", "to_date",
              type=click.DateTime(['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y%m%d']),
              help="The end date to pull data to, required if --to is set, otherwise report will return month to date (UTC).")
@click.option("--granularity",
              type=click.Choice(["None", "Daily"]),
              required=False,
              help="The granularity of rows in the query.")
@output_option()
@query_option()
def workspace_costs(workspace_id, from_date, to_date, granularity, output_format, query):
    log = logging.getLogger(__name__)

    client = ApiClient.get_api_client_from_config()
    url = f"/api/workspaces/{workspace_id}/costs"
    query_string = ""
    if from_date:
        query_string += f"&from_date={from_date}"
    if to_date:
        query_string += f"&to_date={to_date}"
    if granularity:
        query_string += f"&granularity={granularity}"
    if query_string:
        query_string = query_string[1:]  # drop leading ampersand
        url = url + "?" + query_string

    response = client.call_api(log, 'GET', url)
    # TODO - default table format (needs JMESPath let, as per https://jmespath.site/#wiki-lexical-scopes)
    output(
        response,
        output_format=output_format,
        query=query)
    return response.text


costs.add_command(costs_overall)
costs.add_command(workspace_costs)
