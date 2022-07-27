import pytest
import logging
import config
from resources.workspace import get_workspace_auth_details
from resources.resource import disable_and_delete_resource, post_resource
from resources import strings as resource_strings
from airlock.request import post_request, get_request, upload_blob_using_sas, wait_for_status
from airlock import strings as airlock_strings


pytestmark = pytest.mark.asyncio
LOGGER = logging.getLogger(__name__)


@pytest.mark.airlock
@pytest.mark.extended
@pytest.mark.timeout(1200)
async def test_airlock_import_flow(admin_token, verify) -> None:

    # 1. create workspace
    payload = {
        "templateName": "tre-workspace-base",
        "properties": {
            "display_name": "E2E test airlock flow",
            "description": "workspace for E2E airlock flow",
            "address_space_size": "small",
            "client_id": f"{config.TEST_WORKSPACE_APP_ID}",
            "client_secret": f"{config.TEST_WORKSPACE_APP_SECRET}",
        }
    }

    if config.TEST_WORKSPACE_APP_PLAN != "":
        payload["properties"]["app_service_plan_sku"] = config.TEST_WORKSPACE_APP_PLAN

    workspace_path, workspace_id = await post_resource(payload, resource_strings.API_WORKSPACES, access_token=admin_token, verify=verify)
    workspace_owner_token, scope_uri = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)

    # 2. create airlock request
    payload = {
        "requestType": airlock_strings.IMPORT,
        "businessJustification": "some business justification"
    }

    request_result = await post_request(payload, f'/api{workspace_path}/requests', workspace_owner_token, verify, 201)

    assert request_result["airlockRequest"]["requestType"] == airlock_strings.IMPORT
    assert request_result["airlockRequest"]["businessJustification"] == "some business justification"
    assert request_result["airlockRequest"]["status"] == airlock_strings.DRAFT_STATUS

    request_id = request_result["airlockRequest"]["id"]

    # 3. get container link
    request_result = await get_request(f'/api{workspace_path}/requests/{request_id}/link', workspace_owner_token, verify, 200)
    containerUrl = request_result["containerUrl"]

    # 4. upload blob
    await upload_blob_using_sas('./test_airlock_sample.txt', containerUrl)

    # 5. submit request
    request_result = await post_request(None, f'/api{workspace_path}/requests/{request_id}/submit', workspace_owner_token, verify, 200)
    assert request_result["airlockRequest"]["status"] == airlock_strings.SUBMITTED_STATUS

    await wait_for_status(airlock_strings.IN_REVIEW_STATUS, workspace_owner_token, workspace_path, request_id, verify)

    # 6. approve request
    payload = {
        "approval": "True",
        "decisionExplanation": "the reason why this request was approved/rejected"
    }
    request_result = await post_request(payload, f'/api{workspace_path}/requests/{request_id}/reviews', workspace_owner_token, verify, 200)
    assert request_result["airlock_review"]["decisionExplanation"] == "the reason why this request was approved/rejected"

    await wait_for_status(airlock_strings.APPROVED_STATUS, workspace_owner_token, workspace_path, request_id, verify)

    # 7. delete workspace
    await disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify)
