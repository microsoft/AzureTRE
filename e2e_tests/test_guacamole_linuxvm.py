"""Check that a Guacamole Linux VM finishes its Nexus-backed bootstrap."""

from contextlib import AsyncExitStack, asynccontextmanager
from uuid import uuid4

import pytest
from packaging.version import Version

from e2e_tests import config
from e2e_tests.conftest import get_workspace_owner_token
from e2e_tests.helpers import get_admin_token
from e2e_tests.resources import strings
from e2e_tests.resources.resource import get_resource, temporary_resource


pytestmark = pytest.mark.asyncio(loop_scope="session")


@asynccontextmanager
async def linux_vm_nexus(verify):
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
            cert_name = f"nexus-linux-e2e-{uuid4().hex[:8]}"
            await resources.enter_async_context(
                temporary_resource(
                    {
                        "templateName": strings.CERTS_SHARED_SERVICE,
                        "properties": {
                            "display_name": "Linux E2E Nexus certificate",
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
                        "display_name": "Linux E2E Nexus",
                        "ssl_cert_name": cert_name,
                        "accept_nexus_eula": config.TEST_ACCEPT_NEXUS_EULA,
                    },
                },
                strings.API_SHARED_SERVICES,
                admin_token,
                verify,
            )
        )
        yield


@pytest.mark.linux_vm
@pytest.mark.timeout(150 * 60)
async def test_create_guacamole_linux_vm(setup_test_workspace_and_guacamole_service, verify):
    _, workspace_id, workspace_service_path, _ = setup_test_workspace_and_guacamole_service
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)
    payload = {
        "templateName": strings.GUACAMOLE_LINUX_USER_RESOURCE,
        "properties": {
            "display_name": "Nexus Linux bootstrap test",
            "description": "Verify jammy package installation and cloud-init completion",
            "os_image": "Ubuntu 22.04 LTS",
            "vm_size": "2 CPU | 8GB RAM",
        },
    }

    async with linux_vm_nexus(verify):
        async with temporary_resource(
            payload, f"/api{workspace_service_path}/{strings.API_USER_RESOURCES}", workspace_owner_token, verify
        ):
            pass
