import sys
import click
import jmespath
import json
import typing as t
from tabulate import tabulate
from pygments import highlight, lexers, formatters
from enum import Enum
from httpx import Response


class OutputFormat(Enum):
    Suppress = 'none'
    Json = 'json'
    JsonC = 'jsonc'
    Table = 'table'
    Raw = 'raw'


def output_option(*param_decls: str, **kwargs: t.Any):
    param_decls = ('--output', '-o', 'output_format')
    kwargs.setdefault("default", 'table')
    kwargs.setdefault("type", click.Choice(['table', 'json', 'jsonc', 'raw', 'none']))
    kwargs.setdefault("envvar", "TRECLI_OUTPUT")
    kwargs.setdefault("help", "Output format")
    return click.option(*param_decls, **kwargs)


def query_option(*param_decls: str, **kwargs: t.Any):
    param_decls = ('--query', '-q')
    kwargs.setdefault("default", None)
    kwargs.setdefault("help", "JMESPath query to apply to the result")
    return click.option(*param_decls, **kwargs)


def output_result(result_json: str, output_format: OutputFormat = OutputFormat.Json, query: str = None, default_table_query: str = None) -> None:

    if query is None and output_format == OutputFormat.Table.value:
        query = default_table_query

    if query is None:
        output_json = result_json
    else:
        result = json.loads(result_json)
        output = jmespath.search(query, result)
        output_json = json.dumps(output)

    if output_format == OutputFormat.Json.value:
        click.echo(output_json)
    elif output_format == OutputFormat.JsonC.value:
        formatted_json = json.dumps(json.loads(output_json), sort_keys=False, indent=2)
        jsonc = highlight(formatted_json, lexers.JsonLexer(), formatters.TerminalFormatter())
        click.echo(jsonc)
    elif output_format == OutputFormat.Raw.value:
        value = json.loads(output_json)
        click.echo(value)
    elif output_format == OutputFormat.Table.value:
        content = json.loads(output_json)
        if content is not None:
            columns = []
            rows = []

            if type(content) is dict:
                # single item
                item = content
                row = []
                for property_name in item:
                    columns.append(property_name)
                    row.append(item[property_name])
                rows.append(row)
            else:
                if len(content) == 0:
                    # nothing to output
                    return
                item = content[0]
                for property_name in item:
                    columns.append(property_name)
                for item in content:
                    row = []
                    for property_name in item:
                        row.append(item[property_name])
                    rows.append(row)

            click.echo(tabulate(rows, columns))
    else:
        raise click.ClickException(f"Unhandled output format: '{output_format}'")


def output(response: Response, output_format: OutputFormat = OutputFormat.Json, query: str = None, default_table_query: str = None) -> None:

    if output_format == OutputFormat.Suppress.value:
        if not response.is_success:
            sys.exit(1)
        return

    result_json = response.text

    output_result(result_json, output_format, query, default_table_query)

    if not response.is_success:
        sys.exit(1)
