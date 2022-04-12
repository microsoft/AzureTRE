import pytest

from helpers import post_resource
from resources import strings


shared_service_templates = [
    (strings.FIREWALL_SHARED_SERVICE),
    (strings.GITEA_SHARED_SERVICE),
    (strings.NEXUS_SHARED_SERVICE),
]

@pytest.mark.extended
@pytest.mark.parametrize("shared_service_template_name", shared_service_templates)
async def test_patch_shared_service(template_name, admin_token, verify):
    patch_payload = {
        "properties": {
            "display_name": "Updated Firewall Name",
        }
    }

    shared_service_path = f'/shared-services/{template_name}'

    # TODO: path has shared service in it?
    await post_resource(patch_payload, f'/api{shared_service_path}', 'shared_service', admin_token, None, verify, method="PATCH")
