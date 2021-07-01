#!/usr/local/bin/python3

import getopt
import sys
import uuid

from azure.identity import AzureCliCredential
from msgraph.core import GraphClient
from requests.exceptions import HTTPError


def usage():
    print('workspace-app-reg.py -n <tre-name> -w <workspace-name>')


me: dict = None


class Options:
    tre_name: str = None
    workspace_name: str = None
    app_name: str = None
    force: bool = False


options = Options()


class GraphError(Exception):
    def __init__(self, error: dict):
        self.code: str = error['error']['code']
        self.message: str = error['error']['message']
        self.innerError: dict = error['error']['innerError']


class CliGraphClient(GraphClient):
    def __init__(self):
        super().__init__(credential=AzureCliCredential(), scopes=['https://graph.microsoft.com/.default'])

    def get(self, url: str, **kwargs):
        resp = super().get(url, **kwargs)

        try:
            resp.raise_for_status()
        except HTTPError:
            raise GraphError(resp.json())

        json = resp.json()

        if 'value' in json:
            return json['value']

        return json


graph = CliGraphClient()


def _get_commandline_options(argv):
    global options

    try:
        opts, _ = getopt.getopt(argv, "hn:w:f", ["tre-name=", "workspace-name=", "force"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()
        elif opt == '-f':
            options.force = True
        elif opt in ("-n", "--tre-name"):
            options.tre_name = arg
        elif opt in ("-w", "--workspace-name"):
            options.workspace_name = arg

    if options.tre_name is None or options.workspace_name is None:
        usage()
        sys.exit(2)

    options.app_name = f"{options.tre_name} Workspace - {options.workspace_name}"


def get_existing_app(name: str) -> dict:
    apps = graph.get(f"/applications?$filter=displayName eq '{name}'")

    if len(apps) > 1:
        print(f"There are more than one applications with the name \"{name}\" already.")
        sys.exit(1)

    if len(apps) == 1:
        return apps[0]

    return None


def _double_check():
    domains = graph.get("/domains")
    for d in domains:
        if d['isDefault']:
            domain = d['id']
            break

    cont = input(f"You are about to create app registrations in the Azure AD Tenant \"{domain}\", signed in as \"{me['displayName']}\"\nDo you want to continue? (y/N) ")

    if cont.lower() != "y" and cont.lower() != "yes":
        sys.exit(0)


def ensure_sp(appId: str):
    sps = graph.get(f"/servicePrincipals?$filter=appid eq '{appId}'")
    if len(sps) == 0:
        graph.post("/servicePrincipals", json={
            "appId": appId,
            "appRoleAssignmentRequired": True,
            "tags": ['WindowsAzureActiveDirectoryIntegratedApp'],
        }, headers={'Content-Type': 'application/json'})


def main():
    global me
    me = graph.get("/me")

    if not options.force:
        _double_check()

    existing_app = get_existing_app(options.app_name)

    # Generate new Guids if needed
    ownerRoleId = str(uuid.uuid4())
    researcherRoleId = str(uuid.uuid4())

    # Get existing role and scope ids (in case we are updating the existing app)
    if existing_app is not None:
        ownerRoleId = [r['id'] for r in existing_app['appRoles'] if r['value'] == 'WorkspaceOwner'][0]
        researcherRoleId = [r['id'] for r in existing_app['appRoles'] if r['value'] == 'WorkspaceResearcher'][0]

    appRoles = [
        {
            "id": researcherRoleId,
            "allowedMemberTypes": ["User"],
            "description": f"Provides access to the {options.tre_name} workspace {options.workspace_name}.",
            "displayName": "Researchers",
            "isEnabled": True,
            "origin": "Application",
            "value": "WorkspaceResearcher"
        },
        {
            "id": ownerRoleId,
            "allowedMemberTypes": ["User"],
            "description": f"Provides ownership access to the {options.tre_name} workspace {options.workspace_name}.",
            "displayName": "Owners",
            "isEnabled": True,
            "origin": "Application",
            "value": "WorkspaceOwner"
        }
    ]

    # Define the API application
    apiApp = {
        "displayName": options.app_name,
        "appRoles": appRoles,
        "signInAudience": "AzureADMyOrg"
    }

    if existing_app is not None:
        apiAppId = existing_app['appId']
        # Update
        resp = graph.patch(f"/applications/{existing_app['id']}", json=apiApp, headers={'Content-Type': 'application/json'})
        if resp.ok:
            print(f"Updated application \"{existing_app['displayName']}\" (appid={apiAppId})")
        else:
            content = resp.json()
            print(content)
    else:
        # Create
        resp = graph.post(f"/applications", json=apiApp, headers={'Content-Type': 'application/json'})
        content = resp.json()
        if resp.ok:
            apiAppId = content['appId']
            print(f"Created application \"{content['displayName']}\" (appid={apiAppId})")
            graph.post(f"/applications/{content['id']}/owners/$ref")
        else:
            print(content)

    if apiAppId is not None and len(apiAppId) != 0:
        ensure_sp(apiAppId)


if __name__ == "__main__":
    _get_commandline_options(sys.argv[1:])
    main()
