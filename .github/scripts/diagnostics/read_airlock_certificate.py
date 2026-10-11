"""Read only certificate and Nexus metadata for the Airlock validation failure."""

import json
import os
from pathlib import Path
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://tre0f5cf0be.switzerlandnorth.cloudapp.azure.com/api"
CA = ssl.create_default_context(cafile=str(Path(__file__).with_name("tre0f5cf0be.pem")))
TOKEN = ""
TOKEN_TIME = 0.0


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
        # The authority and HTTPS scheme are fixed above.
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
            TOKEN = json.load(response)["access_token"]
        TOKEN_TIME = time.monotonic()
    return TOKEN


def api(endpoint):
    method = "GET"
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


def main():
    code, result = api("/shared-services")
    assert code == 200
    selected = [
        resource
        for resource in result["sharedServices"]
        if resource["templateName"] in ("tre-shared-service-certs", "tre-shared-service-sonatype-nexus")
    ]
    fields = ("id", "templateName", "templateVersion", "isEnabled", "deploymentStatus")
    property_fields = ("display_name", "description", "domain_prefix", "cert_name", "ssl_cert_name")
    operation_fields = ("id", "action", "status", "createdWhen", "updatedWhen", "resourceId")
    for resource in selected:
        safe = {key: resource.get(key) for key in fields}
        safe["properties"] = {key: resource.get("properties", {}).get(key) for key in property_fields}
        code, operations = api(f"/shared-services/{resource['id']}/operations")
        assert code == 200
        safe["operations"] = []
        for operation in operations["operations"]:
            summary = {key: operation.get(key) for key in operation_fields}
            summary["steps"] = [
                {
                    key: step.get(key)
                    for key in ("id", "templateStepId", "resourceId", "resourceAction", "status", "updatedWhen")
                }
                for step in operation.get("steps", [])
            ]
            safe["operations"].append(summary)
        print(json.dumps(safe), flush=True)
    print(json.dumps({"selected_resources": len(selected), "method": "GET"}), flush=True)


if __name__ == "__main__":
    main()
