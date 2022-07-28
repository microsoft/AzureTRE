import pytest
import logging

from resources.resource import disable_and_delete_resource, post_resource
from helpers import get_shared_service_id_by_name
from resources import strings


LOGGER = logging.getLogger(__name__)


@pytest.mark.shared_services
async def test_patch_firewall(admin_token, verify):
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
        },
        "templateName": template_name,
    }

    shared_service_firewall = await get_shared_service_id_by_name(
        template_name, verify, admin_token
    )
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
    (strings.GITEA_SHARED_SERVICE),
    (strings.NEXUS_SHARED_SERVICE),
]


@pytest.mark.shared_services
@pytest.mark.timeout(45 * 60)
@pytest.mark.parametrize("template_name", shared_service_templates_to_create)
async def test_create_shared_service(template_name, admin_token, verify) -> None:
    # Check that the shared service hasn't already been created
    shared_service = await get_shared_service_id_by_name(
        template_name, verify, admin_token
    )
    if shared_service:
        id = shared_service["id"]
        LOGGER.info(
            f"Shared service {template_name} already exists (id {id}), deleting it first..."
        )
        await disable_and_delete_resource(
            f"/api/shared-services/{id}", admin_token, verify
        )

    post_payload = {
        "templateName": template_name,
        "properties": {
            "display_name": f"Shared service {template_name}",
            "description": f"{template_name} deployed via e2e tests",
        },
    }

    shared_service_path, _ = await post_resource(
        payload=post_payload,
        endpoint="/api/shared-services",
        access_token=admin_token,
        verify=verify,
    )

    await disable_and_delete_resource(
        f"/api{shared_service_path}", admin_token, verify
    )
