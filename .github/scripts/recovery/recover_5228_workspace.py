"""Recover only the failed test workspace recorded in issue 5228."""

import json
import os
from pathlib import Path
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

TRE = "tre0f5cf0be"
WORKSPACE = "a9b2bb73-f2cb-4a80-8193-58749a7d38c6"
SERVICE = "29485f52-768b-4933-94e6-3dcf0cd0d01e"
CHILD = "ef61ffc8-99f2-43ea-be80-3b646886dbb8"
GROUP = f"rg-{TRE}-ws-38c6"
VM = "windowsvmdbb8"
NIC = f"internal-nic-{TRE}-ws-38c6-svc-dbb8"
DISK = f"osdisk-{VM}"
VNET = f"vnet-{TRE}-ws-38c6"
SUBSCRIPTION = os.environ["AZURE_SUBSCRIPTION_ID"]
BASE = f"https://{TRE}.switzerlandnorth.cloudapp.azure.com/api"
CA = ssl.create_default_context(cafile=str(Path(__file__).with_name(f"{TRE}.pem")))
EXECUTE = os.environ["EXECUTE_RECOVERY"] == "true"
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
TOKEN = ""
TOKEN_TIME = 0.0


def az(*args):
    result = subprocess.run(
        ["az", *args, "--subscription", SUBSCRIPTION, "-o", "json", "--only-show-errors"],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Azure command failed: {args[:3]}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def token():
    global TOKEN, TOKEN_TIME
    if not TOKEN or time.monotonic() - TOKEN_TIME > 1200:
        tenant = os.environ["AAD_TENANT_ID"]
        body = urllib.parse.urlencode(
            {
                "client_id": os.environ["TEST_ACCOUNT_CLIENT_ID"],
                "client_secret": os.environ["TEST_ACCOUNT_CLIENT_SECRET"],
                "scope": f"api://{os.environ['API_CLIENT_ID']}/.default",
                "grant_type": "client_credentials",
            }
        ).encode()
        request = urllib.request.Request(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data=body)
        with urllib.request.urlopen(request, timeout=30) as response:
            TOKEN = json.load(response)["access_token"]
        TOKEN_TIME = time.monotonic()
    return TOKEN


def api(method, endpoint):
    # Accept only paths under this exact API. Never forward credentials to a redirect.
    assert endpoint.startswith("/") and not endpoint.startswith("//")
    request = urllib.request.Request(BASE + endpoint, method=method, headers={"Authorization": "Bearer " + token()})

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            raise RuntimeError("Unexpected API redirect")

    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CA), NoRedirect())
    try:
        with opener.open(request, timeout=60) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return 404, {}
        raise RuntimeError(f"API {method} {endpoint} failed with HTTP {error.code}") from None


def inventory():
    if not az("group", "exists", "--name", GROUP):
        return []
    return az("resource", "list", "--resource-group", GROUP)


def check_workspace():
    code, result = api("GET", f"/workspaces/{WORKSPACE}")
    assert code == 200
    workspace = result["workspace"]
    assert workspace["id"] == WORKSPACE and workspace["isEnabled"] is False
    assert workspace["deploymentStatus"] == "deleting_failed"
    code, result = api("GET", f"/workspaces/{WORKSPACE}/operations")
    assert code == 200 and result["operations"]
    assert all(operation["status"] in TERMINAL for operation in result["operations"])
    code, active_result = api("GET", "/operations")
    assert code == 200
    assert not any(
        operation["resourceId"] in {WORKSPACE, SERVICE, CHILD}
        or operation.get("resourcePath", "").startswith(f"/workspaces/{WORKSPACE}")
        for operation in active_result["operations"]
    )
    print(
        json.dumps({"workspace": WORKSPACE, "status": workspace["deploymentStatus"], "active_operations": 0}),
        flush=True,
    )


def wait_for_deletion(operation_id):
    deadline = time.monotonic() + 3600
    while time.monotonic() < deadline:
        code, result = api("GET", f"/workspaces/{WORKSPACE}/operations/{operation_id}")
        if code == 404:
            assert api("GET", f"/workspaces/{WORKSPACE}")[0] == 404
            break
        assert code == 200
        current = result["operation"]["status"]
        print(json.dumps({"operation": operation_id, "status": current}), flush=True)
        if current == "deleted":
            break
        assert current not in {"deleting_failed", "deployment_failed", "updating_failed", "action_failed"}
        time.sleep(30)
    else:
        raise TimeoutError("Workspace deletion did not finish within one hour")
    assert api("GET", f"/workspaces/{WORKSPACE}")[0] == 404
    groups = az("group", "list", "--query", f"[?name=='{GROUP}'].name")
    assert not groups or inventory() == []
    print(
        json.dumps(
            {
                "workspace": WORKSPACE,
                "cleanup": "azure_resources_absent_api_resource_absent",
                "child_state": "retained_for_diagnosis",
            }
        ),
        flush=True,
    )


def main():
    assert EXECUTE or os.environ["EXECUTE_RECOVERY"] == "false"
    code, result = api("GET", f"/workspaces/{WORKSPACE}")
    if code == 404:
        assert inventory() == []
        print(json.dumps({"workspace": WORKSPACE, "cleanup": "already_complete"}), flush=True)
        return
    assert code == 200 and result["workspace"]["isEnabled"] is False
    code, result = api("GET", f"/workspaces/{WORKSPACE}/operations")
    assert code == 200
    active = [operation for operation in result["operations"] if operation["status"] not in TERMINAL]
    if active:
        assert len(active) == 1 and active[0]["action"] == "uninstall" and active[0]["resourceId"] == WORKSPACE
        print(json.dumps({"existing_workspace_delete_operation": active[0]["id"], "execute": EXECUTE}), flush=True)
        if EXECUTE:
            wait_for_deletion(active[0]["id"])
        return
    check_workspace()
    resources = inventory()
    allowed = {
        ("microsoft.compute/virtualmachines", VM),
        ("microsoft.compute/virtualmachines/extensions", f"{VM}/{VM}-vmextension"),
        ("microsoft.compute/disks", DISK),
        ("microsoft.network/networkinterfaces", NIC),
        ("microsoft.network/virtualnetworks", VNET),
    }
    assert all((item["type"].lower(), item["name"]) in allowed for item in resources)
    for item in resources:
        assert item["id"].lower().startswith(f"/subscriptions/{SUBSCRIPTION}/resourcegroups/{GROUP}/".lower())
        if item["type"].lower() in {
            "microsoft.compute/virtualmachines",
            "microsoft.network/networkinterfaces",
            "microsoft.compute/disks",
        }:
            assert item["tags"]["tre_id"] == TRE
            assert item["tags"]["tre_workspace_id"] == WORKSPACE
            assert item["tags"]["tre_user_resource_id"] == CHILD
    print(
        json.dumps(
            {"execute": EXECUTE, "azure_resources": [{"id": item["id"], "type": item["type"]} for item in resources]}
        ),
        flush=True,
    )
    if not EXECUTE:
        return
    # The new API patch is deployed with the reviewed processor correction.
    code, metadata = api("GET", "/.metadata")
    assert code == 200 and metadata["api_version"] == "0.28.3"
    check_workspace()
    if any(item["type"].lower() == "microsoft.compute/virtualmachines" for item in resources):
        vm = az("vm", "show", "--resource-group", GROUP, "--name", VM)
        assert vm["storageProfile"]["dataDisks"] == []
        assert vm["storageProfile"]["osDisk"]["managedDisk"]["id"].lower() == (
            f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{GROUP}/providers/Microsoft.Compute/disks/{DISK}".lower()
        )
        assert len(vm["networkProfile"]["networkInterfaces"]) == 1
        assert vm["networkProfile"]["networkInterfaces"][0]["id"].lower() == (
            f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{GROUP}/providers/Microsoft.Network/networkInterfaces/{NIC}".lower()
        )
        az("vm", "delete", "--resource-group", GROUP, "--name", VM, "--yes")
    for kind, name, command in [
        ("microsoft.network/networkinterfaces", NIC, ["network", "nic", "delete"]),
        ("microsoft.compute/disks", DISK, ["disk", "delete"]),
    ]:
        if any(item["type"].lower() == kind and item["name"] == name for item in inventory()):
            args = [*command, "--resource-group", GROUP, "--name", name]
            if kind == "microsoft.compute/disks":
                args.append("--yes")
            az(*args)
    remaining = inventory()
    assert all(
        item["type"].lower() == "microsoft.network/virtualnetworks" and item["name"] == VNET for item in remaining
    )
    check_workspace()
    code, result = api("DELETE", f"/workspaces/{WORKSPACE}")
    assert code == 200
    operation = result["operation"]
    assert operation["resourceId"] == WORKSPACE and operation["action"] == "uninstall"
    operation_id = operation["id"]
    print(json.dumps({"workspace_delete_operation": operation_id}), flush=True)
    wait_for_deletion(operation_id)


if __name__ == "__main__":
    main()
