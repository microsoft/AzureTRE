import pytest

from helpers import disable_and_delete_resource, post_resource, get_shared_service_id_by_name
from resources import strings


@pytest.mark.extended
async def test_patch_firewall(admin_token, verify):
    template_name = strings.FIREWALL_SHARED_SERVICE

    patch_payload = {
        "properties": {
            "display_name": "TEST",
        },
        "templateName": template_name,
    }

    shared_service_firewall = await get_shared_service_id_by_name(template_name, verify, admin_token)
    shared_service_path = f'/shared-services/{shared_service_firewall["id"]}'

    await post_resource(patch_payload, f'/api{shared_service_path}', 'shared_service', admin_token, None, verify, method="PATCH")


shared_service_templates_to_create = [
    (strings.GITEA_SHARED_SERVICE),
    (strings.NEXUS_SHARED_SERVICE),
]


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

    shared_service_path, _ = await post_resource(post_payload, '/api/shared-services', 'shared_service', admin_token, None, verify)

    await disable_and_delete_resource(f'/api{shared_service_path}', 'shared_service', admin_token, None, verify)
