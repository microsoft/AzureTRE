import pytest

from helpers import disable_and_delete_resource, post_resource
from resources import strings


@pytest.mark.skip
@pytest.mark.extended
async def test_patch_firewall(admin_token, verify):
    template_name = "tre-shared-service-firewall"

    patch_payload = {
        "properties": {
            "display_name": "TEST",
        },
        "templateName": template_name,
    }

    shared_service_path = f'/shared-services/{template_name}'

    await post_resource(patch_payload, f'/api{shared_service_path}', 'shared_service', admin_token, None, verify, method="PATCH")


shared_service_templates_to_create = [
    # (strings.GITEA_SHARED_SERVICE),
    (strings.NEXUS_SHARED_SERVICE),
]


@pytest.mark.skip
@pytest.mark.extended
@pytest.mark.timeout(30 * 60)
@pytest.mark.parametrize("template_name", shared_service_templates_to_create)
async def test_create_shared_service(template_name, admin_token, workspace_owner_token, verify) -> None:
    post_payload = {
        "templateName": template_name,
        "properties": {
            "display_name": f"Shared service {template_name}",
            "description": f"{template_name} deployed via e2e tests"
        }
    }

    await post_resource(post_payload, '/api/shared-services', 'shared_service', admin_token, None, verify)

    shared_service_path = f'/shared-services/{template_name}'
    await disable_and_delete_resource(f'/api{shared_service_path}', 'workspace_service', workspace_owner_token, None, verify)
