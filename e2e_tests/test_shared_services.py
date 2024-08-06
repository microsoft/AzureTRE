import pytest
import logging
from e2e_tests.conftest import disable_and_delete_tre_resource
from datetime import date

from resources.resource import post_resource
from helpers import get_shared_service_by_name
from resources import strings
from helpers import get_admin_token

LOGGER = logging.getLogger(__name__)


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
                            "target_fqdns": [
                                "one.two.three.microsoft.com",
                                "two.three.microsoft.com"
                            ],
                            "source_addresses": ["172.196.0.0"]
                        }
                    ]
                },
                {
                    "name": "e2e-rule-collection-2",
                    "action": "Allow",
                    "rules": [
                        {
                            "name": "e2e test rule 1",
                            "description": "desc here",
                            "protocols": [{"port": "5556", "type": "Http"}],
                            "target_fqdns": [
                                "one.two.microsoft.com",
                                "two.microsoft.com"
                            ],
                            "source_addresses": ["172.196.0.1"]
                        }
                    ]
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
                            "target_fqdns": [
                                "one.two.three.microsoft.com.uk"
                            ],
                            "source_addresses": ["172.196.0.2"]
                        }
                    ]
                }
            ],
        }
    }

    admin_token = await get_admin_token(verify)
    shared_service_firewall = await get_shared_service_by_name(
        template_name, verify, admin_token
    )

    if shared_service_firewall:
        shared_service_path = f'/shared-services/{shared_service_firewall["id"]}'

        await post_resource(
            payload=patch_payload,
            endpoint=f"/api{shared_service_path}",
            access_token=admin_token,
            verify=verify,
            method="PATCH",
            etag=shared_service_firewall['_etag'],
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
@pytest.mark.timeout(50 * 60)
@pytest.mark.parametrize("template_name", shared_service_templates_to_create)
async def test_create_shared_service(template_name, verify) -> None:
    await disable_and_delete_shared_service_if_exists(template_name, verify)

    post_payload = {
        "templateName": template_name,
        "properties": {
            "display_name": f"Shared service {template_name}",
            "description": f"{template_name} deployed via e2e tests",
        },
    }

    if template_name == strings.AIRLOCK_NOTIFIER_SHARED_SERVICE:
        post_payload["properties"].update(create_airlock_notifier_properties)

    admin_token = await get_admin_token(verify)

    shared_service_path, _ = await post_resource(
        payload=post_payload,
        endpoint="/api/shared-services",
        access_token=admin_token,
        verify=verify,
    )

    await disable_and_delete_tre_resource(shared_service_path, verify)


@pytest.mark.shared_services
@pytest.mark.timeout(60 * 60)
@pytest.mark.skipif(date.today().weekday() in [5, 6], reason="LetsEncrypt limits to 5 times a week. Skipping on SAT & SUN.")
async def test_create_certs_nexus_shared_service(verify) -> None:
    await disable_and_delete_shared_service_if_exists(strings.NEXUS_SHARED_SERVICE, verify)
    await disable_and_delete_shared_service_if_exists(strings.CERTS_SHARED_SERVICE, verify)

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
        },
    }

    admin_token = await get_admin_token(verify)

    certs_shared_service_path, _ = await post_resource(
        payload=certs_post_payload,
        endpoint="/api/shared-services",
        access_token=admin_token,
        verify=verify,
    )

    nexus_shared_service_path, _ = await post_resource(
        payload=nexus_post_payload,
        endpoint="/api/shared-services",
        access_token=admin_token,
        verify=verify,
    )

    await disable_and_delete_tre_resource(nexus_shared_service_path, verify)

    await disable_and_delete_tre_resource(certs_shared_service_path, verify)


async def disable_and_delete_shared_service_if_exists(shared_service_name, verify) -> None:
    admin_token = await get_admin_token(verify)

    # Check that the shared service hasn't already been created
    shared_service = await get_shared_service_by_name(
        shared_service_name, verify, admin_token
    )
    if shared_service:
        id = shared_service["id"]
        LOGGER.info(
            f"Shared service {shared_service_name} already exists (id {id}), deleting it first..."
        )
        await disable_and_delete_tre_resource(f"/shared-services/{id}", verify)
