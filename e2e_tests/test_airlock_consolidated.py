"""
E2E tests for v2 consolidated airlock storage.

These tests verify the full airlock lifecycle using consolidated storage
(metadata-based stage management with ABAC workspace_id filtering).
The workspace defaults to airlock_version=2.

Tests that can run from a CI runner outside the workspace VNet:
- Import: draft -> upload (core storage, public) -> submit -> in_review -> approve/reject
- Export: draft creation and storage account verification (can't upload - workspace storage is private)
"""
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
    """Helper: create import draft, upload a file, submit, wait for in_review."""
    payload = {
        "type": airlock_strings.IMPORT,
        "businessJustification": "E2E test import"
    }
    result = await post_request(payload, f'/api{workspace_path}/requests', workspace_owner_token, verify, 201)
    request_id = result["airlockRequest"]["id"]
    assert result["airlockRequest"]["status"] == airlock_strings.DRAFT_STATUS

    # Get container URL - should be core storage (stalairlock, not stalairlockg)
    link_result = await get_request(
        f'/api{workspace_path}/requests/{request_id}/link',
        workspace_owner_token, verify, 200
    )
    container_url = link_result["containerUrl"]
    assert "stalairlock" in container_url and "stalairlockg" not in container_url, \
        f"Import draft should use core storage, got: {container_url}"

    # Upload blob (core storage allows public access for import-external)
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
    assert blob_uploaded, "Failed to upload blob after retries"

    # Submit
    result = await post_request(None, f'/api{workspace_path}/requests/{request_id}/submit', workspace_owner_token, verify, 200)
    assert result["airlockRequest"]["status"] == airlock_strings.SUBMITTED_STATUS

    await wait_for_status(airlock_strings.IN_REVIEW_STATUS, workspace_owner_token, workspace_path, request_id, verify)

    return request_id, container_url


@pytest.mark.timeout(35 * 60)
@pytest.mark.airlock
async def test_v2_import_approve_flow(setup_test_workspace, verify):
    """Full v2 import lifecycle: draft -> upload -> submit -> in_review -> approve -> approved."""
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    request_id, container_url = await create_and_submit_import(workspace_path, workspace_owner_token, verify)
    LOGGER.info(f"Import request {request_id} is in_review")

    # Approve
    payload = {
        "approval": "True",
        "decisionExplanation": "Approved for E2E test"
    }
    result = await post_request(payload, f'/api{workspace_path}/requests/{request_id}/review', workspace_owner_token, verify, 200)
    assert result["airlockRequest"]["reviews"][0]["decisionExplanation"] == "Approved for E2E test"

    await wait_for_status(airlock_strings.APPROVED_STATUS, workspace_owner_token, workspace_path, request_id, verify)
    LOGGER.info(f"Import request {request_id} approved")

    # Verify the container name is consistent (same request_id container throughout)
    def extract_container_name(url):
        m = re.match(r'https://[^/]+/([^?]+)', url)
        return m.group(1) if m else None

    assert extract_container_name(container_url) == request_id, \
        f"Container name should be request_id {request_id}"


@pytest.mark.timeout(35 * 60)
@pytest.mark.airlock
async def test_v2_import_reject_flow(setup_test_workspace, verify):
    """V2 import rejection: draft -> upload -> submit -> in_review -> reject -> rejected."""
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    request_id, _ = await create_and_submit_import(workspace_path, workspace_owner_token, verify)
    LOGGER.info(f"Import request {request_id} is in_review, rejecting")

    # Reject
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
    """V2 import cancellation from draft state."""
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    # Create draft
    payload = {
        "type": airlock_strings.IMPORT,
        "businessJustification": "E2E cancel test"
    }
    result = await post_request(payload, f'/api{workspace_path}/requests', workspace_owner_token, verify, 201)
    request_id = result["airlockRequest"]["id"]
    assert result["airlockRequest"]["status"] == airlock_strings.DRAFT_STATUS

    # Wait for container to be created
    await asyncio.sleep(10)

    # Cancel
    result = await post_request(None, f'/api{workspace_path}/requests/{request_id}/cancel', workspace_owner_token, verify, 200)
    assert result["airlockRequest"]["status"] == airlock_strings.CANCELLED_STATUS
    LOGGER.info(f"Import request {request_id} cancelled from draft")


@pytest.mark.timeout(10 * 60)
@pytest.mark.airlock
async def test_v2_export_uses_workspace_storage(setup_test_workspace, verify):
    """V2 export draft should use global workspace storage (stalairlockg)."""
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

    assert "stalairlockg" in container_url, \
        f"Export draft should use global workspace storage (stalairlockg), got: {container_url}"
    LOGGER.info(f"Export request uses correct storage: {container_url}")


@pytest.mark.timeout(10 * 60)
@pytest.mark.airlock
async def test_v2_import_uses_core_storage(setup_test_workspace, verify):
    """V2 import draft should use core storage (stalairlock, not stalairlockg)."""
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

    assert "stalairlock" in container_url and "stalairlockg" not in container_url, \
        f"Import draft should use core storage (stalairlock), got: {container_url}"
    LOGGER.info(f"Import request uses correct storage: {container_url}")
