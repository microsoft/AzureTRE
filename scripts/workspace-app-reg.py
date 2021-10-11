#!/usr/local/bin/python3

import click
import sys
import uuid

from azure.identity import AzureCliCredential
from msgraph.core import GraphClient


class GraphError(Exception):
    def __init__(self, message: str, error: dict):
        if error:
            self.code: str = error['error']['code']
            self.message: str = f"{message}: {error['error']['message']}"
            self.innerError: dict = error['error']['innerError']
        else:
            self.message: str = message


class CliGraphClient(GraphClient):
    def __init__(self):
        super().__init__(credential=AzureCliCredential(), scopes=['https://graph.microsoft.com/.default'])

    def get(self, url: str, **kwargs):
        resp = super().get(url, **kwargs)

        if not resp.ok:
            raise GraphError(f"Error calling GET {url}", resp.json())

        json = resp.json()

        if 'value' in json:
            return json['value']

        return json

    def me(self):
        return self.get("/me")

    def default_domain(self):
        domains = self.get("/domains")
        for d in domains:
            if d['isDefault']:
                return d['id']

    def get_existing_app(self, name: str) -> dict:
        apps = self.get(f"/applications?$filter=displayName eq '{name}'")

        if len(apps) > 1:
            raise GraphError(f"There is more than one application with the name \"{name}\" already.", None)

        if len(apps) == 1:
            return apps[0]

        return None

    def create_app(self, app: dict) -> dict:
        resp = self.post("/applications", json=app, headers={'Content-Type': 'application/json'})

        if not resp.ok:
            raise GraphError("Error creating application", resp.json())

        return resp.json()

    def update_app(self, app_object_id: str, app: dict) -> dict:
        resp = self.patch(f"/applications/{app_object_id}", json=app, headers={'Content-Type': 'application/json'})
        if not resp.ok:
            raise GraphError("Error updating application", resp.json())
        # Now get the updated app details
        resp = super().get(f"/applications/{app_object_id}")
        if not resp.ok:
            raise GraphError("Error getting updating application", resp.json())
        return resp.json()

    def ensure_sp(self, appId: str, roleAssignmentRequired: bool):
        sp = {"appId": appId, "appRoleAssignmentRequired": roleAssignmentRequired, "tags": ['WindowsAzureActiveDirectoryIntegratedApp']}
        sps = self.get(f"/servicePrincipals?$filter=appid eq '{appId}'")
        if len(sps) == 0:
            resp = self.post("/servicePrincipals", json=sp, headers={'Content-Type': 'application/json'})
            if not resp.ok:
                raise GraphError("Error creating service principal", resp.json())
        else:
            resp = self.patch(f"/servicePrincipals/{sps[0]['id']}", json=sp, headers={'Content-Type': 'application/json'})
            if not resp.ok:
                raise GraphError("Error updating service principal", resp.json())


def double_check(domain: str, myname: str) -> bool:
    should_continue = input(f"You are about to create app registrations in the Azure AD Tenant \"{domain}\", signed in as \"{myname}\"\nDo you want to continue? (y/N) ")
    return True if should_continue.lower() == "y" or should_continue.lower() == "yes" else False


def get_role_id(app: dict, role: str) -> str:
    if app:
        ids = [r['id'] for r in app['appRoles'] if r['value'] == role]
        if len(ids) == 1:
            return ids[0]

    return str(uuid.uuid4())


@click.command()
@click.option('-n', '--tre-name', required=True)
@click.option('-w', '--workspace-name', required=True)
@click.option('-f', '--force', is_flag=True, default=False)
def main(tre_name, workspace_name, force):
    graph = CliGraphClient()

    try:

        if not force and not double_check(graph.default_domain(), graph.me()['displayName']):
            sys.exit(0)

        app_name = f"{tre_name} Workspace - {workspace_name}"
        existing_app = graph.get_existing_app(app_name)

        # Define the App Roles
        appRoles = [
            {
                "id": get_role_id(existing_app, 'WorkspaceResearcher'),
                "allowedMemberTypes": ["User"],
                "description": f"Provides access to the {tre_name} workspace {workspace_name}.",
                "displayName": "Researchers",
                "isEnabled": True,
                "origin": "Application",
                "value": "WorkspaceResearcher"
            },
            {
                "id": get_role_id(existing_app, 'WorkspaceOwner'),
                "allowedMemberTypes": ["User"],
                "description": f"Provides ownership access to the {tre_name} workspace {workspace_name}.",
                "displayName": "Owners",
                "isEnabled": True,
                "origin": "Application",
                "value": "WorkspaceOwner"
            }
        ]

        # Define the API application
        workspaceApp = {
            "displayName": app_name,
            "appRoles": appRoles,
            "signInAudience": "AzureADMyOrg"
        }

        if existing_app:
            app = graph.update_app(existing_app['id'], workspaceApp)
            print(f"Updated application \"{app['displayName']}\" (appid={app['appId']})")
        else:
            app = graph.create_app(workspaceApp)
            print(f"Created application \"{app['displayName']}\" (appid={app['appId']})")

        if app:
            graph.ensure_sp(app['appId'], True)

    except GraphError as graph_error:
        print(graph_error.message)
        sys.exit(1)


if __name__ == "__main__":
    main()
