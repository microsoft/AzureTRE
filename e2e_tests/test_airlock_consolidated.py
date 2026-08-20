import re
import pytest
import asyncio
import logging

from airlock.request import post_request, get_request, upload_blob_using_sas, wait_for_status
from airlock import strings as airlock_strings
from e2e_tests.conftest import get_workspace_owner_token


pytestmark = pytest.mark.asyncio(loop_scope="session")
LOGGER = logging.getLogger(__name__)
BLOB_FILE_PATH = "./test_airlock_sample.txt"


async def create_and_submit_import(workspace_path, workspace_owner_token, verify):
    payload = {
        "type": airlock_strings.IMPORT,
        "businessJustification": "E2E test import"
    }
    result = await post_request(payload, f'/api{workspace_path}/requests', workspace_owner_token, verify, 201)
    request_id = result["airlockRequest"]["id"]
    assert result["airlockRequest"]["status"] == airlock_strings.DRAFT_STATUS

    link_result = await get_request(
        f'/api{workspace_path}/requests/{request_id}/link',
        workspace_owner_token, verify, 200
    )
    container_url = link_result["containerUrl"]
    assert "stalairlock" in container_url and "stalairlockg" not in container_url

    blob_uploaded = False
    for attempt in range(5):
        try:
            await asyncio.sleep(5)
            upload_response = await upload_blob_using_sas(BLOB_FILE_PATH, container_url)
            if "etag" in upload_response:
                blob_uploaded = True
                break
        except Exception:
            LOGGER.info(f"Upload attempt {attempt + 1} failed, retrying...")
            await asyncio.sleep(10)
    assert blob_uploaded

    result = await post_request(None, f'/api{workspace_path}/requests/{request_id}/submit', workspace_owner_token, verify, 200)
    assert result["airlockRequest"]["status"] == airlock_strings.SUBMITTED_STATUS

    await wait_for_status(airlock_strings.IN_REVIEW_STATUS, workspace_owner_token, workspace_path, request_id, verify)

    return request_id, container_url


@pytest.mark.timeout(35 * 60)
@pytest.mark.airlock
async def test_v2_import_approve_flow(setup_test_workspace, verify):
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    request_id, container_url = await create_and_submit_import(workspace_path, workspace_owner_token, verify)
    LOGGER.info(f"Import request {request_id} is in_review")

    payload = {
        "approval": "True",
        "decisionExplanation": "Approved for E2E test"
    }
    result = await post_request(payload, f'/api{workspace_path}/requests/{request_id}/review', workspace_owner_token, verify, 200)
    assert result["airlockRequest"]["reviews"][0]["decisionExplanation"] == "Approved for E2E test"

    await wait_for_status(airlock_strings.APPROVED_STATUS, workspace_owner_token, workspace_path, request_id, verify)
    LOGGER.info(f"Import request {request_id} approved")

    def extract_container_name(url):
        m = re.match(r'https://[^/]+/([^?]+)', url)
        return m.group(1) if m else None

    # The link handed out in Draft points at the draft container, which submission seals away.
    assert extract_container_name(container_url) == f"{request_id}-draft"

    approved_link = await get_request(
        f'/api{workspace_path}/requests/{request_id}/link',
        workspace_owner_token, verify, 200
    )
    assert extract_container_name(approved_link["containerUrl"]) == request_id


@pytest.mark.timeout(35 * 60)
@pytest.mark.airlock
async def test_v2_import_reject_flow(setup_test_workspace, verify):
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    request_id, _ = await create_and_submit_import(workspace_path, workspace_owner_token, verify)
    LOGGER.info(f"Import request {request_id} is in_review, rejecting")

    payload = {
        "approval": "False",
        "decisionExplanation": "Rejected for E2E test"
    }
    result = await post_request(payload, f'/api{workspace_path}/requests/{request_id}/review', workspace_owner_token, verify, 200)
    assert result["airlockRequest"]["reviews"][0]["decisionExplanation"] == "Rejected for E2E test"

    await wait_for_status(airlock_strings.REJECTED_STATUS, workspace_owner_token, workspace_path, request_id, verify)
    LOGGER.info(f"Import request {request_id} rejected")


@pytest.mark.timeout(10 * 60)
@pytest.mark.airlock
async def test_v2_import_cancel(setup_test_workspace, verify):
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    payload = {
        "type": airlock_strings.IMPORT,
        "businessJustification": "E2E cancel test"
    }
    result = await post_request(payload, f'/api{workspace_path}/requests', workspace_owner_token, verify, 201)
    request_id = result["airlockRequest"]["id"]
    assert result["airlockRequest"]["status"] == airlock_strings.DRAFT_STATUS

    await asyncio.sleep(10)

    result = await post_request(None, f'/api{workspace_path}/requests/{request_id}/cancel', workspace_owner_token, verify, 200)
    assert result["airlockRequest"]["status"] == airlock_strings.CANCELLED_STATUS
    LOGGER.info(f"Import request {request_id} cancelled from draft")


@pytest.mark.timeout(10 * 60)
@pytest.mark.airlock
async def test_v2_export_uses_workspace_storage(setup_test_workspace, verify):
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    payload = {
        "type": airlock_strings.EXPORT,
        "businessJustification": "E2E export storage test"
    }
    result = await post_request(payload, f'/api{workspace_path}/requests', workspace_owner_token, verify, 201)
    request_id = result["airlockRequest"]["id"]

    link_result = await get_request(
        f'/api{workspace_path}/requests/{request_id}/link',
        workspace_owner_token, verify, 200
    )
    container_url = link_result["containerUrl"]

    assert "stalairlockg" in container_url
    LOGGER.info(f"Export request uses correct storage: {container_url}")


@pytest.mark.timeout(10 * 60)
@pytest.mark.airlock
async def test_v2_import_uses_core_storage(setup_test_workspace, verify):
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    payload = {
        "type": airlock_strings.IMPORT,
        "businessJustification": "E2E import storage test"
    }
    result = await post_request(payload, f'/api{workspace_path}/requests', workspace_owner_token, verify, 201)
    request_id = result["airlockRequest"]["id"]

    link_result = await get_request(
        f'/api{workspace_path}/requests/{request_id}/link',
        workspace_owner_token, verify, 200
    )
    container_url = link_result["containerUrl"]

    assert "stalairlock" in container_url and "stalairlockg" not in container_url
    LOGGER.info(f"Import request uses correct storage: {container_url}")
