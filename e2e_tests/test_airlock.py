import os
import pytest
import asyncio
import logging

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import ContainerClient

from resources.workspace import get_workspace_auth_details
from airlock.request import post_request, get_request, upload_blob_using_sas, wait_for_status
from airlock import strings as airlock_strings


pytestmark = pytest.mark.asyncio
LOGGER = logging.getLogger(__name__)
BLOB_FILE_PATH = "./test_airlock_sample.txt"
BLOB_NAME = os.path.basename(BLOB_FILE_PATH)


@pytest.mark.airlock
@pytest.mark.extended
@pytest.mark.timeout(35 * 60)
async def test_airlock_flow(verify, workspace, admin_token) -> None:
    workspace_id, workspace_path, workspace_owner_token = workspace
    workspace_owner_token, = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)

    # 2. create airlock request
    LOGGER.info("Creating airlock import request")
    payload = {
        "type": airlock_strings.IMPORT,
        "businessJustification": "some business justification"
    }

    request_result = await post_request(payload, f'/api{workspace_path}/requests', workspace_owner_token, verify, 201)

    assert request_result["airlockRequest"]["type"] == airlock_strings.IMPORT
    assert request_result["airlockRequest"]["businessJustification"] == "some business justification"
    assert request_result["airlockRequest"]["status"] == airlock_strings.DRAFT_STATUS

    request_id = request_result["airlockRequest"]["id"]

    # 3. get container link
    LOGGER.info("Getting airlock request container URL")
    request_result = await get_request(f'/api{workspace_path}/requests/{request_id}/link', workspace_owner_token, verify, 200)
    container_url = request_result["containerUrl"]

    # 4. upload blob

    # currenly there's no elegant way to check if the container was created yet becasue its an asyc process
    # it would be better to create another draft_improgress step and wait for the request to change to draft state before
    # uploading the blob

    i = 1
    blob_uploaded = False
    wait_time = 30
    while not blob_uploaded:
        LOGGER.info(f"try #{i} to upload a blob to container [{container_url}]")
        upload_response = await upload_blob_using_sas(BLOB_FILE_PATH, container_url)

        if upload_response.status_code == 404:
            i += 1
            LOGGER.info(f"sleeping for {wait_time} sec until container would be created")
            await asyncio.sleep(wait_time)
        else:
            assert upload_response.status_code == 201
            LOGGER.info("upload blob succeeded")
            blob_uploaded = True

    # 5. submit request
    LOGGER.info("Submitting airlock request")
    request_result = await post_request(None, f'/api{workspace_path}/requests/{request_id}/submit', workspace_owner_token, verify, 200)
    assert request_result["airlockRequest"]["status"] == airlock_strings.SUBMITTED_STATUS

    await wait_for_status(airlock_strings.IN_REVIEW_STATUS, workspace_owner_token, workspace_path, request_id, verify)

    # 6. approve request
    LOGGER.info("Approving airlock request")
    payload = {
        "approval": "True",
        "decisionExplanation": "the reason why this request was approved/rejected"
    }
    request_result = await post_request(payload, f'/api{workspace_path}/requests/{request_id}/review', workspace_owner_token, verify, 200)
    assert request_result["airlockRequest"]["reviews"][0]["decisionExplanation"] == "the reason why this request was approved/rejected"

    await wait_for_status(airlock_strings.APPROVED_STATUS, workspace_owner_token, workspace_path, request_id, verify)

    # 7. check the file has been deleted from the source
    # NOTE: We should really be checking that the file is deleted from in progress location too,
    # but doing that will require setting up network access to in-progress storage account
    try:
        container_client = ContainerClient.from_container_url(container_url=container_url)
        # We expect the container to eventually be deleted too, but sometimes this async operation takes some time.
        # Checking that at least there are no blobs within the container
        for _ in container_client.list_blobs():
            container_url_without_sas = container_url.split("?")[0]
            assert False, f"The source blob in container {container_url_without_sas} should be deleted"
    except ResourceNotFoundError:
        # Expecting this exception
        pass

    # 8. get a link to the blob in the approved location.
    # For a full E2E we should try to download it, but can't without special networking setup.
    # So at the very least we check that we get the link for it.
    request_result = await get_request(f'/api{workspace_path}/requests/{request_id}/link', workspace_owner_token, verify, 200)
    container_url = request_result["containerUrl"]

    # 9. create airlock export request
    LOGGER.info("Creating airlock export request")
    justification = "another business justification"
    payload = {
        "type": airlock_strings.EXPORT,
        "businessJustification": justification
    }

    request_result = await post_request(payload, f'/api{workspace_path}/requests', workspace_owner_token, verify, 201)

    assert request_result["airlockRequest"]["type"] == airlock_strings.EXPORT
    assert request_result["airlockRequest"]["businessJustification"] == justification
    assert request_result["airlockRequest"]["status"] == airlock_strings.DRAFT_STATUS

    request_id = request_result["airlockRequest"]["id"]

    # 10. get container link
    LOGGER.info("Getting airlock request container URL")
    request_result = await get_request(f'/api{workspace_path}/requests/{request_id}/link', workspace_owner_token, verify, 200)
    container_url = request_result["containerUrl"]
    # we can't test any more the export flow since we don't have the network
    # access to upload the file from within the workspace.
