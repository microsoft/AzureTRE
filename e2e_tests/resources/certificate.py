"""Read public certificate and cleanup evidence without accessing vault secrets."""

import asyncio
import base64
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import os
import re
from uuid import UUID

from cryptography import x509
from cryptography.hazmat.primitives import hashes

from e2e_tests import config
from e2e_tests.cloud import get_cloud
from e2e_tests.resources.sql_probe import arm_client


NETWORK_API = "2024-05-01"
STORAGE_API = "2023-05-01"
LOGS_API = "2023-09-01"
CHECK_TIMEOUT_SECONDS = 5 * 60


def certificate_metadata(gateway, public_ip, group, tre_id, resource_id):
    """Return only public metadata after checking resource ownership and identity."""
    expected_tags = {"tre_id": tre_id, "tre_shared_service_id": resource_id}
    for resource, suffix in (
        (gateway, f"Microsoft.Network/applicationGateways/agw-certs-{tre_id}"),
        (public_ip, f"Microsoft.Network/publicIPAddresses/pip-cert-nexus-{tre_id}"),
    ):
        assert resource.get("id", "").lower() == f"{group}/providers/{suffix}".lower(), (
            "Unexpected certificate resource"
        )
        assert all(resource.get("tags", {}).get(k) == v for k, v in expected_tags.items()), (
            "Certificate infrastructure does not belong to this test-created service"
        )
    fqdn = public_ip["properties"]["dnsSettings"]["fqdn"]
    certificates = [c for c in gateway["properties"].get("sslCertificates", []) if c["name"] == "cert-primary"]
    assert len(certificates) == 1, "The gateway must have one primary certificate"
    properties = certificates[0]["properties"]
    secret_id = properties.get("keyVaultSecretId", "")
    assert re.fullmatch(
        rf"https://kv-{re.escape(tre_id)}\.vault\.azure\.net/secrets/nexus-ssl/[a-fA-F0-9]+", secret_id
    ), "The gateway certificate must reference the named certificate in the core vault"
    data = base64.b64decode(properties["publicCertData"], validate=True)
    cert = (
        x509.load_pem_x509_certificate(data)
        if data.startswith(b"-----BEGIN CERTIFICATE-----")
        else x509.load_der_x509_certificate(data)
    )
    names = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert fqdn in names.get_values_for_type(x509.DNSName), "Certificate SAN does not match the service hostname"
    now = datetime.now(timezone.utc)
    assert cert.not_valid_before_utc <= now, "Certificate is not valid yet"
    assert cert.not_valid_after_utc > now + timedelta(days=30), "Certificate is already due for renewal"
    return {"hostname": fqdn, "sha256": cert.fingerprint(hashes.SHA256()).hex()}


def reuse_query(resource_id, digest):
    # Only validated identifiers enter the query. Return counts, never raw logs.
    resource_id = str(UUID(resource_id))
    if not re.fullmatch("[a-f0-9]{64}", digest):
        raise ValueError("Expected a SHA-256 certificate fingerprint")
    return f"""
let received = AppTraces
| where Message contains 'Message received for resource_id={resource_id},'
| where isnotempty(OperationId)
| distinct OperationId;
AppTraces
| where OperationId in (received)
| summarize
    reused=countif(Message contains 'Reusing certificate nexus-ssl, SHA-256 fingerprint {digest}; no ACME request required'),
    issued=countif(Message contains 'Certificate issuance required:'),
    completed=countif(Message contains 'Message for resource_id={resource_id},' and Message contains 'processed as True and marked complete.')
"""


def query_counts(response):
    if response.get("error"):
        raise RuntimeError("Certificate log query returned incomplete evidence")
    tables = [table for table in response.get("tables", []) if table.get("name") == "PrimaryResult"]
    if len(tables) != 1 or len(tables[0].get("rows", [])) != 1:
        raise RuntimeError("Certificate log query did not return one evidence row")
    names = [column["name"] for column in tables[0]["columns"]]
    values = tables[0]["rows"][0]
    if names != ["reused", "issued", "completed"] or len(values) != 3:
        raise RuntimeError("Certificate log query returned unexpected columns")
    if any(type(value) is not int or value < 0 for value in values):
        raise RuntimeError("Certificate log query returned invalid counts")
    return dict(zip(names, values, strict=True))


class CertificateChecks:
    def __init__(self, arm, subscription_id, tre_id):
        subscription_id = str(UUID(subscription_id))
        if not re.fullmatch("[a-z0-9][a-z0-9-]{1,20}", tre_id):
            raise ValueError("Expected the deployed TRE identifier")
        self.arm = arm
        self.tre_id = tre_id
        self.group = f"/subscriptions/{subscription_id}/resourceGroups/rg-{tre_id}"
        self.gateway_id = f"{self.group}/providers/Microsoft.Network/applicationGateways/agw-certs-{tre_id}"
        self.ip_id = f"{self.group}/providers/Microsoft.Network/publicIPAddresses/pip-cert-nexus-{tre_id}"
        storage = f"stwebcerts{tre_id}".replace("-", "")
        self.storage_id = f"{self.group}/providers/Microsoft.Storage/storageAccounts/{storage}"
        self.logs_id = None

    async def prepare(self):
        workspace = await self.arm.request(
            "GET", f"{self.group}/providers/Microsoft.OperationalInsights/workspaces/log-{self.tre_id}", LOGS_API
        )
        self.logs_id = str(UUID(workspace["properties"]["customerId"]))
        # Check query access before recovering or creating any shared service.
        await self.query(reuse_query("00000000-0000-0000-0000-000000000000", "0" * 64))

    async def query(self, query):
        token = await asyncio.to_thread(self.arm.credential.get_token, "https://api.loganalytics.io/.default")
        response = await self.arm.client.post(
            f"https://api.loganalytics.azure.com/v1/workspaces/{self.logs_id}/query",
            headers={"Authorization": f"Bearer {token.token}"},
            json={"query": query, "timespan": "PT6H"},
            follow_redirects=False,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Certificate log query failed with HTTP {response.status_code}")
        return query_counts(response.json())

    async def snapshot(self, resource_path):
        resource_id = str(UUID(resource_path.rsplit("/", 1)[-1]))
        async with asyncio.timeout(CHECK_TIMEOUT_SECONDS):
            while True:
                gateway = await self.arm.request("GET", self.gateway_id, NETWORK_API)
                if gateway["properties"].get("operationalState") == "Stopped":
                    break
                await asyncio.sleep(10)
            public_ip = await self.arm.request("GET", self.ip_id, NETWORK_API)
            evidence = certificate_metadata(gateway, public_ip, self.group, self.tre_id, resource_id)
            return {**evidence, "gateway_stopped": True}

    async def confirm_reuse(self, resource_path, digest):
        query = reuse_query(resource_path.rsplit("/", 1)[-1], digest)
        async with asyncio.timeout(CHECK_TIMEOUT_SECONDS):
            while True:
                counts = await self.query(query)
                assert counts["issued"] == 0, "Reinstallation entered the ACME issuance path"
                if counts["reused"] > 0 and counts["completed"] > 0:
                    return
                await asyncio.sleep(10)

    async def confirm_removed(self):
        async with asyncio.timeout(CHECK_TIMEOUT_SECONDS):
            while True:
                remaining = []
                for resource_id, api in (
                    (self.gateway_id, NETWORK_API),
                    (self.ip_id, NETWORK_API),
                    (self.storage_id, STORAGE_API),
                ):
                    if await self.arm.request("GET", resource_id, api, missing_ok=True) is not None:
                        remaining.append(resource_id)
                if not remaining:
                    return
                await asyncio.sleep(10)


@asynccontextmanager
async def certificate_checks():
    # Match the existing ARM helper. Do not send tokens to guessed cloud endpoints.
    if get_cloud().name != "AzureCloud":
        raise ValueError("Certificate lifecycle evidence currently supports AzureCloud only")
    async with arm_client() as arm:
        checks = CertificateChecks(arm, os.environ["ARM_SUBSCRIPTION_ID"], config.TRE_ID)
        await checks.prepare()
        yield checks
