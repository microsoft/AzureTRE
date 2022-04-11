import pytest

from httpx import
from httpx import AsyncClient
from starlette import status

import config
from urllib.parse import urljoin
from helpers import get_auth_header, get_template
from resources import strings


shared_service_templates = [
    (strings.FIREWALL_SHARED_SERVICE),
    (strings.GITEA_SHARED_SERVICE),
    (strings.NEXUS_SHARED_SERVICE),
]

@pytest.mark.smoke
@pytest.mark.parametrize("shared_service_template_name", shared_service_templates)
async def test_patch_shared_service(template_name, admin_token, verify)
    async with AsyncClient(verify=verify) as client:
        patch_payload = {
            "properties": {
                "display_name": "Updated Guac Name",
            }
        }

        # TODO: my API is stupid and can't get an item by name :(
        shared_service_path = urljoin('/api/')

        # TODO: path has shared service in it?
        await post_resource(patch_payload, f'/api{workspace_service_path}', 'shared_service', admin_token, None, verify, method="PATCH")
