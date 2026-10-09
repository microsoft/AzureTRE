"""One-off API recovery of the disabled review workspace recorded in #5183."""

import json
import os
from pathlib import Path
import ssl
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SUBSCRIPTION = "5f49ca61-f6b3-44c3-b5f8-3da00aa35cd0"
TRE = "tre06624892"
ORIGIN = f"https://{TRE}.switzerlandnorth.cloudapp.azure.com"
WORKSPACE = "ccbe6423-3465-4fe3-9ded-28d0fec39e3b"
SERVICE = "630a4969-8c67-44b0-8da1-6caa31fcbbb4"
VM = "8d3324f3-98a6-44f9-a953-be2803613e7c"
WORKSPACE_PATH = f"/api/workspaces/{WORKSPACE}"
TERMINAL = {
    "deployed",
    "deployment_failed",
    "updated",
    "updating_failed",
    "deleted",
    "deleting_failed",
    "action_succeeded",
    "action_failed",
}


def main():
    action = os.environ["RECOVERY_ACTION"]
    assert action in ("inspect", "status", "delete")
    temporary = Path(os.environ["RUNNER_TEMP"])
    group = json.loads((temporary / "airlock-core-group.json").read_text())
    assert group["id"].lower() == f"/subscriptions/{SUBSCRIPTION}/resourcegroups/rg-{TRE}"
    assert group["tags"]["tre_id"] == TRE
    assert group["tags"]["ci_git_ref"] == "refs/pull/5165/merge"
    # Public certificate read from the configured Key Vault secret via the resource processor.
    api_tls = ssl.create_default_context(cafile=str(Path(__file__).with_name("airlock_5183_api.pem")))
    tokens = {}

    def token(scope):
        if scope not in tokens or tokens[scope][1] < time.monotonic():
            fields = {
                "client_id": os.environ["TEST_ACCOUNT_CLIENT_ID"],
                "client_secret": os.environ["TEST_ACCOUNT_CLIENT_SECRET"],
                "grant_type": "client_credentials",
                "scope": f"{scope}/.default",
            }
            url = f"https://login.microsoftonline.com/{os.environ['AAD_TENANT_ID']}/oauth2/v2.0/token"
            with urlopen(Request(url, data=urlencode(fields).encode()), timeout=30) as response:  # nosec B310 - fixed HTTPS authority
                result = json.load(response)
            tokens[scope] = (result["access_token"], time.monotonic() + int(result["expires_in"]) - 120)
        return tokens[scope][0]

    def api(path, scope, method="GET", etag=None):
        # Only relative API paths may receive a bearer token.
        assert path.startswith(WORKSPACE_PATH) and not path.startswith("//")
        headers = {"Authorization": f"Bearer {token(scope)}"}
        if etag:
            headers["etag"] = etag
        request = Request(ORIGIN + path, method=method, headers=headers)
        with urlopen(request, context=api_tls, timeout=60) as response:  # nosec B310 - fixed HTTPS origin
            return json.load(response), response.headers

    admin_scope = f"api://{os.environ['API_CLIENT_ID']}"
    if action == "status":
        try:
            operations = api(WORKSPACE_PATH + "/operations", admin_scope)[0]["operations"]
        except HTTPError as error:
            if error.code != 404:
                raise
            print("Workspace no longer present.")
            return
        for operation in operations:
            print(json.dumps({"id": operation["id"], "state": operation["status"],
                              "steps": [{"title": step["stepTitle"], "state": step["status"],
                                         "resource_id": step["resourceId"]}
                                        for step in operation["steps"]]}))
        return
    workspace = api(WORKSPACE_PATH, admin_scope)[0]["workspace"]
    assert workspace["id"] == WORKSPACE
    assert workspace["templateName"] == "tre-workspace-airlock-import-review"
    workspace_scope = "api://" + workspace["properties"]["scope_id"].removeprefix("api://")
    services_path = WORKSPACE_PATH + "/workspace-services"
    services = api(services_path, workspace_scope)[0]["workspaceServices"]
    assert [item["id"] for item in services] == [SERVICE], "Unexpected service inventory"
    assert services[0]["templateName"] == "tre-service-guacamole"
    service_path = services_path + "/" + SERVICE
    resources = api(service_path + "/user-resources", workspace_scope)[0]["userResources"]
    assert [item["id"] for item in resources] == [VM], "Unexpected VM inventory"
    assert resources[0]["templateName"] == "tre-service-guacamole-import-reviewvm"

    for resource, path, scope in (
        (workspace, WORKSPACE_PATH, admin_scope),
        (services[0], service_path, workspace_scope),
        (resources[0], service_path + "/user-resources/" + VM, workspace_scope),
    ):
        operations = api(path + "/operations", scope)[0]["operations"]
        print(
            json.dumps(
                {
                    "id": resource["id"],
                    "template": resource["templateName"],
                    "enabled": resource["isEnabled"],
                    "state": resource["deploymentStatus"],
                    "operations": [{"id": operation["id"], "state": operation["status"]} for operation in operations],
                }
            )
        )
        if action == "delete":
            assert resource["isEnabled"] is False, "Resource must already be disabled"
            assert resource["deploymentStatus"] in TERMINAL, "Resource has not reached a terminal state"
            assert all(operation["status"] in TERMINAL for operation in operations), "Active operation present"

    if action == "inspect":
        print("Inspection complete. No resources changed.")
        return

    result, headers = api(WORKSPACE_PATH, admin_scope, "DELETE", workspace["_etag"])
    operation = result["operation"]
    assert operation["resourceId"] == WORKSPACE
    location = headers["Location"]
    assert location.startswith(WORKSPACE_PATH + "/operations/")
    print(json.dumps({"delete_operation": operation["id"]}))
    deadline = time.monotonic() + 3600
    while time.monotonic() < deadline:
        try:
            operation = api(location, admin_scope)[0]["operation"]
        except HTTPError as error:
            if error.code != 404:
                raise
            print("Workspace deletion completed (operation no longer present).")
            return
        print(
            json.dumps(
                {
                    "state": operation["status"],
                    "steps": [{"id": step["id"], "state": step["status"]} for step in operation["steps"]],
                }
            )
        )
        if operation["status"] == "deleted":
            print("Workspace deletion completed.")
            return
        assert operation["status"] != "deleting_failed", "Workspace deletion failed; inspect operation logs"
        time.sleep(30)
    raise TimeoutError("Workspace deletion did not complete within one hour")


if __name__ == "__main__":
    main()
