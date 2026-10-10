"""Nexus prerequisites shared by Linux and Airlock review VM tests."""

from contextlib import AsyncExitStack, asynccontextmanager
from uuid import uuid4

from packaging.version import Version

from e2e_tests import config
from e2e_tests.helpers import get_admin_token
from e2e_tests.resources import strings
from e2e_tests.resources.resource import (
    FAILED_CREATE_CLEANUP_TIMEOUT_SECONDS,
    disable_and_delete_resource,
    get_resource,
    post_resource,
    temporary_resource,
)
from e2e_tests.timeouts import cleanup_deadline


async def cleanup_certificate(resource_path, access_token, verify):
    async with cleanup_deadline(FAILED_CREATE_CLEANUP_TIMEOUT_SECONDS):
        services = (await get_resource(strings.API_SHARED_SERVICES, access_token, verify))["sharedServices"]
        if any(service["templateName"] == strings.NEXUS_SHARED_SERVICE for service in services):
            raise RuntimeError(f"Retaining certificate dependency {resource_path}: Nexus is still present")
        await disable_and_delete_resource(f"/api{resource_path}", access_token, verify, allow_failed_disable=True)


@asynccontextmanager
async def certificate_prerequisite(payload, endpoint, access_token, verify):
    resource_path, _ = await post_resource(payload, endpoint, access_token, verify, cleanup_failed_create=True)
    try:
        yield resource_path
    except BaseException as original_error:
        try:
            await cleanup_certificate(resource_path, access_token, verify)
        except Exception as cleanup_error:
            original_error.add_note(f"Cleanup of {resource_path} also failed: {cleanup_error!r}")
        raise
    else:
        await cleanup_certificate(resource_path, access_token, verify)


@asynccontextmanager
async def nexus_prerequisites(verify):
    """Reuse a suitable Nexus instance or create explicitly authorised prerequisites."""
    admin_token = await get_admin_token(verify)
    services = (await get_resource(strings.API_SHARED_SERVICES, admin_token, verify))["sharedServices"]
    nexus_services = [service for service in services if service["templateName"] == strings.NEXUS_SHARED_SERVICE]
    assert len(nexus_services) <= 1, "This test requires at most one Nexus shared service"
    if nexus_services:
        nexus = nexus_services[0]
        assert nexus["isEnabled"] and nexus["deploymentStatus"] in ("deployed", "updated"), (
            "Nexus must be deployed and enabled"
        )
        assert Version(nexus["templateVersion"]) >= Version("3.11.0"), "Upgrade Nexus to bundle 3.11.0 before this test"
        yield
        return

    assert config.TEST_ACCEPT_NEXUS_EULA, (
        "This test requires Nexus. Deploy Nexus 3.11.0 first, or explicitly accept its CE EULA "
        "with TEST_ACCEPT_NEXUS_EULA=true (acceptNexusEula in the branch workflow)."
    )
    cert_services = [service for service in services if service["templateName"] == strings.CERTS_SHARED_SERVICE]
    assert len(cert_services) <= 1, "This test requires at most one certificate shared service"
    async with AsyncExitStack() as resources:
        if cert_services:
            certs = cert_services[0]
            assert certs["isEnabled"] and certs["deploymentStatus"] in ("deployed", "updated"), (
                "Repair the existing Nexus certificate service before this test"
            )
            assert certs["properties"].get("domain_prefix") == "nexus", (
                "The existing certificate service belongs to another domain. Deploy Nexus separately before this test."
            )
            cert_name = certs["properties"]["cert_name"]
        else:
            cert_name = f"nexus-e2e-{uuid4().hex[:8]}"
            await resources.enter_async_context(
                certificate_prerequisite(
                    {
                        "templateName": strings.CERTS_SHARED_SERVICE,
                        "properties": {
                            "display_name": "E2E Nexus certificate",
                            "description": "Certificate prerequisite for E2E Nexus",
                            "domain_prefix": "nexus",
                            "cert_name": cert_name,
                        },
                    },
                    strings.API_SHARED_SERVICES,
                    admin_token,
                    verify,
                )
            )
        await resources.enter_async_context(
            temporary_resource(
                {
                    "templateName": strings.NEXUS_SHARED_SERVICE,
                    "properties": {
                        "display_name": "E2E Nexus",
                        "description": "Nexus prerequisite for E2E workspace resources",
                        "ssl_cert_name": cert_name,
                        "accept_nexus_eula": config.TEST_ACCEPT_NEXUS_EULA,
                        "vm_size": "Standard_D2s_v3",
                    },
                },
                strings.API_SHARED_SERVICES,
                admin_token,
                verify,
            )
        )
        yield
