"""Read one public certificate through the resource processor's private network."""

import base64
import http.client
import json
import re
import sys
from urllib.parse import urlencode, urlsplit
from uuid import UUID


PREFIX = "TRE_PUBLIC_CERTIFICATE="


def read_json(connection, path, headers):
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError(f"Public certificate probe received HTTP {response.status}")
        content = response.read(65537)
        if len(content) > 65536:
            raise ValueError("Public certificate probe response exceeds its limit")
        return json.loads(content)
    finally:
        connection.close()


def read_certificate(certificate_url, client_id):
    if not re.fullmatch(
        r"https://kv-[a-z0-9][a-z0-9-]{1,20}\.vault\.azure\.net/certificates/nexus-ssl/[a-fA-F0-9]+",
        certificate_url,
    ):
        raise ValueError("Expected a versioned public certificate in the core vault")
    client_id = str(UUID(client_id))
    query = urlencode({"api-version": "2018-02-01", "resource": "https://vault.azure.net", "client_id": client_id})
    token = read_json(
        http.client.HTTPConnection("169.254.169.254", timeout=10),
        "/metadata/identity/oauth2/token?" + query,
        {"Metadata": "true"},
    )["access_token"]
    parsed = urlsplit(certificate_url)
    certificate = read_json(
        http.client.HTTPSConnection(parsed.hostname, timeout=30),
        parsed.path + "?api-version=7.4",
        {"Authorization": "Bearer " + token},
    )
    secret_id = certificate_url.replace("/certificates/", "/secrets/")
    if certificate.get("id") != certificate_url or certificate.get("sid") != secret_id:
        raise ValueError("Public certificate version does not match the gateway reference")
    if certificate.get("attributes", {}).get("enabled") is not True:
        raise ValueError("The referenced certificate is disabled")
    base64.b64decode(certificate["cer"], validate=True)
    result = {key: certificate[key] for key in ("id", "sid", "cer")}
    output = PREFIX + json.dumps(result, separators=(",", ":"))
    # Managed Run Command retains only the final 4 KiB of output.
    if len(output.encode()) > 3500:
        raise ValueError("Public certificate exceeds the Run Command output limit")
    return output


if __name__ == "__main__":
    try:
        print(read_certificate(sys.argv[1], sys.argv[2]))
    except Exception:
        # Do not print credentials, response bodies or exception values.
        print("Public certificate probe failed", file=sys.stderr)
        sys.exit(1)
