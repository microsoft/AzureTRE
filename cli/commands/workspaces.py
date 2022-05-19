import json
from pprint import pprint
import click
from openapi_client import ApiClient, Configuration, ApiException
from openapi_client.api import workspaces_api
from .auth import get_token

config_file = open('config.json')
config = json.load(config_file)

api_config = Configuration(host=config["endpoint"])
api_config.verify_ssl = False


def list(format):
    token = get_token()
    if token is None:
        click.echo("Please login")
        return
    api_config.access_token = token

    with ApiClient(api_config) as api_client:
        ws_api = workspaces_api.WorkspacesApi(api_client)

        try:
            ws_resp = ws_api.get_all_workspaces_api_workspaces_get()
            if format == "text":
                for ws in ws_resp["workspaces"]:
                    click.echo(ws["id"] + '\t' + ws["properties"]["display_name"])
            elif format == "json":
                out = []
                for ws in ws_resp["workspaces"]:
                    out.append({
                        "id": ws["id"],
                        "properties": ws["properties"]
                    })
                click.echo(json.dumps(out, indent=2))
        except ApiException as e:
            print("Exception: %s\n" % e)


def show(workspace_id, format):
    token = get_token()
    if token is None:
        click.echo("Please login")
        return
    api_config.access_token = token

    with ApiClient(api_config) as api_client:
        ws_api = workspaces_api.WorkspacesApi(api_client)

        try:
            ws_resp = ws_api.get_workspace_by_id_api_workspaces_workspace_id_get(workspace_id)
            ws = ws_resp["workspace"]
            if format == "text":
                click.echo(ws["id"] + '\t' + ws["properties"]["display_name"])
            elif format == "json":
                click.echo(json.dumps({
                    "id": ws["id"],
                    "properties": ws["properties"]
                }, indent=2))
        except ApiException as e:
            print("Exception: %s\n" % e)
