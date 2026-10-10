import asyncio
from contextlib import AsyncExitStack, asynccontextmanager

import pytest
import logging
from e2e_tests import config
from e2e_tests.conftest import disable_and_delete_tre_resource
from datetime import date

from resources.resource import (
    FAILED_CREATE_CLEANUP_TIMEOUT_SECONDS,
    disable_and_delete_resource,
    get_resource,
    post_resource,
)
from helpers import get_shared_service_by_name
from resources import strings
from helpers import get_admin_token

LOGGER = logging.getLogger(__name__)
RECOVERY_TIMEOUT_SECONDS = 60 * 60
PROVISIONING_TIMEOUT_SECONDS = 60 * 60
CLEANUP_TIMEOUT_SECONDS = 60 * 60
# Recover old resources under one shared deadline. Failed creation can spend
# another cleanup deadline inside post_resource before unwinding the exit stack.
SINGLE_SERVICE_TIMEOUT_SECONDS = (
    RECOVERY_TIMEOUT_SECONDS
    + PROVISIONING_TIMEOUT_SECONDS
    + max(CLEANUP_TIMEOUT_SECONDS, FAILED_CREATE_CLEANUP_TIMEOUT_SECONDS)
    + 30 * 60
)
NEXUS_TIMEOUT_SECONDS = (
    RECOVERY_TIMEOUT_SECONDS
    + PROVISIONING_TIMEOUT_SECONDS
    + max(2 * CLEANUP_TIMEOUT_SECONDS, FAILED_CREATE_CLEANUP_TIMEOUT_SECONDS + CLEANUP_TIMEOUT_SECONDS)
    + 30 * 60
)
TERMINAL_STATES = {
    "deployed",
    "deployment_failed",
    "updated",
    "updating_failed",
    "deleted",
    "deleting_failed",
    "action_succeeded",
    "action_failed",
    "pipeline_succeeded",
    "pipeline_failed",
}


async def cleanup_created_shared_service(payload, resource_path, verify):
    async with asyncio.timeout(CLEANUP_TIMEOUT_SECONDS):
        if payload["templateName"] == strings.CERTS_SHARED_SERVICE:
            admin_token = await get_admin_token(verify)
            if await get_shared_service_by_name(strings.NEXUS_SHARED_SERVICE, verify, admin_token):
                raise RuntimeError(f"Retaining certificate dependency {resource_path}: Nexus is still present")
        await disable_and_delete_tre_resource(resource_path, verify)


@asynccontextmanager
async def managed_shared_service(payload, verify):
    admin_token = await get_admin_token(verify)
    resource_path, _ = await post_resource(
        payload=payload,
        endpoint=strings.API_SHARED_SERVICES,
        access_token=admin_token,
        verify=verify,
        cleanup_failed_create=True,
    )
    try:
        yield resource_path
    except BaseException as original_error:
        try:
            await cleanup_created_shared_service(payload, resource_path, verify)
        except Exception as cleanup_error:
            original_error.add_note(f"Cleanup of {resource_path} also failed: {cleanup_error!r}")
        raise
    else:
        await cleanup_created_shared_service(payload, resource_path, verify)


@pytest.mark.shared_services
async def test_patch_firewall(verify):
    template_name = strings.FIREWALL_SHARED_SERVICE

    patch_payload = {
        "properties": {
            "display_name": "TEST",
            "rule_collections": [
                {
                    "name": "e2e-rule-collection-1",
                    "action": "Allow",
                    "rules": [
                        {
                            "name": "e2e test rule 1",
                            "description": "desc here",
                            "protocols": [{"port": "5555", "type": "Http"}],
                            "target_fqdns": ["one.two.three.microsoft.com", "two.three.microsoft.com"],
                            "source_addresses": ["172.196.0.0"],
                        }
                    ],
                },
                {
                    "name": "e2e-rule-collection-2",
                    "action": "Allow",
                    "rules": [
                        {
                            "name": "e2e test rule 1",
                            "description": "desc here",
                            "protocols": [{"port": "5556", "type": "Http"}],
                            "target_fqdns": ["one.two.microsoft.com", "two.microsoft.com"],
                            "source_addresses": ["172.196.0.1"],
                        }
                    ],
                },
                {
                    "name": "e2e-rule-collection-3",
                    "action": "Allow",
                    "priority": 501,
                    "rules": [
                        {
                            "name": "e2e test rule 1",
                            "description": "desc here",
                            "protocols": [{"port": "5557", "type": "Http"}],
                            "target_fqdns": ["one.two.three.microsoft.com.uk"],
                            "source_addresses": ["172.196.0.2"],
                        }
                    ],
                },
            ],
        }
    }

    admin_token = await get_admin_token(verify)
    shared_service_firewall = await get_shared_service_by_name(template_name, verify, admin_token)

    assert shared_service_firewall, (
        f"Firewall shared service '{template_name}' not found. Deploy it before running this test."
    )
    shared_service_path = f"/shared-services/{shared_service_firewall['id']}"

    await post_resource(
        payload=patch_payload,
        endpoint=f"/api{shared_service_path}",
        access_token=admin_token,
        verify=verify,
        method="PATCH",
        etag=shared_service_firewall["_etag"],
    )


shared_service_templates_to_create = [
    strings.GITEA_SHARED_SERVICE,
    strings.ADMIN_VM_SHARED_SERVICE,
    # Tested in test_create_certs_nexus_shared_service
    # strings.NEXUS_SHARED_SERVICE,
    strings.AIRLOCK_NOTIFIER_SHARED_SERVICE,
    # TODO: fix cyclecloud and enable this
    # strings.CYCLECLOUD_SHARED_SERVICE,
]

create_airlock_notifier_properties = {
    "smtp_server_address": "10.1.2.3",
    "smtp_username": "smtp_user",
    "smtpPassword": "abcdefg01234567890",
    "smtp_from_email": "a@a.com",
}


@pytest.mark.shared_services
@pytest.mark.timeout(SINGLE_SERVICE_TIMEOUT_SECONDS)
@pytest.mark.parametrize("template_name", shared_service_templates_to_create)
async def test_create_shared_service(template_name, verify) -> None:
    await recover_previous_shared_services(verify, template_name)

    post_payload = {
        "templateName": template_name,
        "properties": {
            "display_name": f"Shared service {template_name}",
            "description": f"{template_name} deployed via e2e tests",
        },
    }

    if template_name == strings.ADMIN_VM_SHARED_SERVICE:
        post_payload["properties"]["admin_jumpbox_vm_sku"] = "Standard_D2s_v3"

    if template_name == strings.AIRLOCK_NOTIFIER_SHARED_SERVICE:
        post_payload["properties"].update(create_airlock_notifier_properties)

    async with AsyncExitStack() as resources:
        async with asyncio.timeout(PROVISIONING_TIMEOUT_SECONDS):
            await resources.enter_async_context(managed_shared_service(post_payload, verify))


@pytest.mark.shared_services
@pytest.mark.nexus
@pytest.mark.timeout(NEXUS_TIMEOUT_SECONDS)
async def test_create_certs_nexus_shared_service(verify) -> None:
    if not config.TEST_ACCEPT_NEXUS_EULA:
        pytest.fail(
            "Nexus CE EULA acceptance is required; Nexus lifecycle coverage is unproven. "
            "After accepting the EULA, set TEST_ACCEPT_NEXUS_EULA=true locally, "
            "acceptNexusEula=true in the branch workflow, or add accept_nexus_eula "
            "to /test-shared-services. No Nexus or certificate resources were changed."
        )
    if date.today().weekday() in [5, 6] and not config.TEST_RUN_CERTIFICATE_TESTS_ON_WEEKENDS:
        pytest.skip("Certificate rate-limit precaution: skipping on weekends; Nexus lifecycle coverage is unproven.")

    await recover_previous_shared_services(verify, strings.NEXUS_SHARED_SERVICE, strings.CERTS_SHARED_SERVICE)

    cert_domain = "nexus"
    cert_name = "nexus-ssl"

    certs_post_payload = {
        "templateName": strings.CERTS_SHARED_SERVICE,
        "properties": {
            "display_name": f"Shared service {strings.CERTS_SHARED_SERVICE}",
            "description": f"{strings.CERTS_SHARED_SERVICE} deployed via e2e tests",
            "domain_prefix": cert_domain,
            "cert_name": cert_name,
        },
    }

    nexus_post_payload = {
        "templateName": strings.NEXUS_SHARED_SERVICE,
        "properties": {
            "display_name": f"Shared service {strings.NEXUS_SHARED_SERVICE}",
            "description": f"{strings.NEXUS_SHARED_SERVICE} deployed via e2e tests",
            "ssl_cert_name": cert_name,
            "vm_size": "Standard_D2s_v3",
            "accept_nexus_eula": config.TEST_ACCEPT_NEXUS_EULA,
        },
    }

    # Provisioning cancellation unwinds before cleanup starts. Each owned
    # resource then receives a separate finite cleanup deadline.
    async with AsyncExitStack() as resources:
        async with asyncio.timeout(PROVISIONING_TIMEOUT_SECONDS):
            await resources.enter_async_context(managed_shared_service(certs_post_payload, verify))
            await resources.enter_async_context(managed_shared_service(nexus_post_payload, verify))


async def recover_previous_shared_services(verify, *template_names):
    # Share this budget across all prior resources, before creating new ones.
    async with asyncio.timeout(RECOVERY_TIMEOUT_SECONDS):
        for template_name in template_names:
            await disable_and_delete_shared_service_if_exists(template_name, verify)


async def disable_and_delete_shared_service_if_exists(shared_service_name, verify) -> None:
    admin_token = await get_admin_token(verify)

    # Check that the shared service hasn't already been created
    shared_service = await get_shared_service_by_name(shared_service_name, verify, admin_token)
    if shared_service:
        properties = shared_service.get("properties", {})
        assert (
            properties.get("display_name") == f"Shared service {shared_service_name}"
            and properties.get("description") == f"{shared_service_name} deployed via e2e tests"
        ), "Refusing cleanup of a shared service not created by this test"
        resource_id = shared_service["id"]
        endpoint = f"/api/shared-services/{resource_id}"
        async with asyncio.timeout(CLEANUP_TIMEOUT_SECONDS):
            while True:
                operations = (await get_resource(endpoint + "/operations", admin_token, verify))["operations"]
                if all(operation["status"] in TERMINAL_STATES for operation in operations):
                    break
                await asyncio.sleep(30)
            LOGGER.info("Recovering prior E2E shared service %s (%s)", shared_service_name, resource_id)
            await disable_and_delete_resource(endpoint, admin_token, verify, allow_failed_disable=True)
