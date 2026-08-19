import os
import pytest
import asyncio
import logging

from azure.core.exceptions import ResourceNotFoundError

from airlock.request import post_request, get_request, upload_blob_using_sas, delete_blob_using_sas, wait_for_status
from resources.resource import get_resource, post_resource
from resources.workspace import get_workspace_auth_details
from airlock import strings as airlock_strings
from e2e_tests.conftest import get_workspace_owner_token
from helpers import get_admin_token


pytestmark = pytest.mark.asyncio(loop_scope="session")
LOGGER = logging.getLogger(__name__)
BLOB_FILE_PATH = "./test_airlock_sample.txt"
BLOB_NAME = os.path.basename(BLOB_FILE_PATH)
SECOND_BLOB_FILE_PATH = "./test_airlock_second_sample.txt"


async def submit_airlock_import_request(workspace_path: str, workspace_owner_token: str, verify: bool):
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

    # get container link
    LOGGER.info("Getting airlock request container URL")
    request_result = await get_request(f'/api{workspace_path}/requests/{request_id}/link', workspace_owner_token, verify, 200)
    container_url = request_result["containerUrl"]

    # upload blob

    # currenly there's no elegant way to check if the container was created yet becasue its an asyc process
    # it would be better to create another draft_improgress step and wait for the request to change to draft state before
    # uploading the blob

    i = 1
    blob_uploaded = False
    wait_time = 30
    while not blob_uploaded:
        LOGGER.info(f"try #{i} to upload a blob to container [{container_url}]")
        try:
            await asyncio.sleep(5)
            upload_response = await upload_blob_using_sas(BLOB_FILE_PATH, container_url)
            if "etag" in upload_response:
                blob_uploaded = True
            else:
                raise Exception("upload failed")
        except ResourceNotFoundError:
            i += 1
            LOGGER.info(f"sleeping for {wait_time} sec until container would be created")
            await asyncio.sleep(wait_time)
            pass
        except Exception as e:
            LOGGER.error(f"upload blob failed with exception: {e}")
            raise e

    # submit request
    LOGGER.info("Submitting airlock request")
    request_result = await post_request(None, f'/api{workspace_path}/requests/{request_id}/submit', workspace_owner_token, verify, 200)
    assert request_result["airlockRequest"]["status"] == airlock_strings.SUBMITTED_STATUS

    await wait_for_status(airlock_strings.IN_REVIEW_STATUS, workspace_owner_token, workspace_path, request_id, verify)

    return request_id, container_url


@pytest.mark.timeout(30 * 60)
@pytest.mark.airlock
async def test_draft_container_is_sealed_after_submit(setup_test_workspace, verify):
    """A SAS handed out while the request was in Draft must stop working once it is submitted,
    otherwise a researcher could alter the data after it has been scanned and reviewed."""
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    _, container_url = await submit_airlock_import_request(workspace_path, workspace_owner_token, verify)

    # Submission copies the data out and deletes the draft container, so the old SAS resolves to nothing.
    with pytest.raises(ResourceNotFoundError):
        await upload_blob_using_sas(BLOB_FILE_PATH, container_url)


async def create_draft_import_request_with_file(workspace_path: str, workspace_owner_token: str, verify: bool):
    payload = {
        "type": airlock_strings.IMPORT,
        "businessJustification": "some business justification"
    }
    request_result = await post_request(payload, f'/api{workspace_path}/requests', workspace_owner_token, verify, 201)
    request_id = request_result["airlockRequest"]["id"]

    request_result = await get_request(f'/api{workspace_path}/requests/{request_id}/link', workspace_owner_token, verify, 200)
    container_url = request_result["containerUrl"]

    # Container creation is asynchronous, so a successful upload is what confirms it exists.
    for _ in range(20):
        try:
            await asyncio.sleep(5)
            upload_response = await upload_blob_using_sas(BLOB_FILE_PATH, container_url)
            if "etag" in upload_response:
                return request_id, container_url
        except ResourceNotFoundError:
            await asyncio.sleep(30)
    raise Exception("Draft container was not created in time")


async def submit_and_expect_failure(workspace_path, workspace_owner_token, request_id, verify, expected_message):
    await post_request(None, f'/api{workspace_path}/requests/{request_id}/submit', workspace_owner_token, verify, 200)
    await wait_for_status(airlock_strings.FAILED_STATUS, workspace_owner_token, workspace_path, request_id, verify)

    request_result = await get_request(f'/api{workspace_path}/requests/{request_id}', workspace_owner_token, verify, 200)
    assert expected_message in request_result["airlockRequest"]["statusMessage"]


@pytest.mark.timeout(30 * 60)
@pytest.mark.airlock
async def test_submit_with_no_files_is_rejected(setup_test_workspace, verify):
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    request_id, container_url = await create_draft_import_request_with_file(workspace_path, workspace_owner_token, verify)
    await delete_blob_using_sas(BLOB_FILE_PATH, container_url)

    await submit_and_expect_failure(workspace_path, workspace_owner_token, request_id, verify, "did not contain any files")


@pytest.mark.timeout(30 * 60)
@pytest.mark.airlock
async def test_submit_with_multiple_files_is_rejected(setup_test_workspace, verify):
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    request_id, container_url = await create_draft_import_request_with_file(workspace_path, workspace_owner_token, verify)

    # upload_blob_using_sas names the blob after the file, so a second distinct name is needed.
    with open(SECOND_BLOB_FILE_PATH, "w") as second_file:
        second_file.write("a second file in the same request")
    await upload_blob_using_sas(SECOND_BLOB_FILE_PATH, container_url)

    await submit_and_expect_failure(workspace_path, workspace_owner_token, request_id, verify, "more than 1 file")


@pytest.mark.timeout(50 * 60)
@pytest.mark.airlock
async def test_airlock_review_vm_flow(setup_test_workspace, setup_test_airlock_import_review_workspace_and_guacamole_service, verify):
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    _, import_review_workspace_id, _, import_review_workspace_service_id = setup_test_airlock_import_review_workspace_and_guacamole_service

    # Preparation: Update the research workspace so that it has the import review details
    patch_payload = {
        "properties": {
            "enable_airlock": True,
            "configure_review_vms": True,
            "airlock_review_config": {
                "import": {
                    "import_vm_workspace_id": import_review_workspace_id,
                    "import_vm_workspace_service_id": import_review_workspace_service_id,
                    "import_vm_user_resource_template_name": "tre-service-guacamole-import-reviewvm"
                },
                "export": {
                    "export_vm_workspace_service_id": "",
                    "export_vm_user_resource_template_name": "tre-service-guacamole-export-reviewvm"
                }
            }
        }
    }
    # Get workspace to get the etag
    workspace = await get_resource(f"/api{workspace_path}", workspace_owner_token, verify)
    admin_token = await get_admin_token(verify)

    await post_resource(
        payload=patch_payload,
        endpoint=f"/api{workspace_path}",
        access_token=admin_token,
        verify=verify,
        method="PATCH",
        etag=workspace["workspace"]["_etag"],
    )
    LOGGER.info("Workspace Airlock Review confiuguration set up")

    # IMPORT FLOW
    # Submit the request
    request_id, _ = await submit_airlock_import_request(workspace_path, workspace_owner_token, verify)

    LOGGER.info(f'Airlock Request ID {request_id} has been created')

    # Create a review VM
    admin_token = await get_admin_token(verify)
    import_workspace_owner_token, _ = await get_workspace_auth_details(admin_token=admin_token, workspace_id=import_review_workspace_id, verify=verify)

    # The request belongs to the research workspace, so it must not be reachable by id through
    # another workspace the caller happens to have access to.
    await get_request(f'/api/workspaces/{import_review_workspace_id}/requests/{request_id}', import_workspace_owner_token, verify, 404)

    user_resource_path, user_resource_id = await post_resource(
        payload={},
        endpoint=f"/api{workspace_path}/requests/{request_id}/review-user-resource",
        access_token=workspace_owner_token,
        verify=verify,
        method="POST",
        wait=True,
        access_token_for_wait=import_workspace_owner_token  # needs a different token as is created in a separate workspace
    )

    LOGGER.info(f"Airlock Review VM has been created: {user_resource_path}")

    # Approve request
    LOGGER.info("Approving airlock request")
    payload = {
        "approval": "True",
        "decisionExplanation": "the reason why this request was approved/rejected"
    }
    request_result = await post_request(payload, f'/api{workspace_path}/requests/{request_id}/review', workspace_owner_token, verify, 200)
    assert request_result["airlockRequest"]["reviews"][0]["decisionExplanation"] == "the reason why this request was approved/rejected"

    await wait_for_status(airlock_strings.APPROVED_STATUS, workspace_owner_token, workspace_path, request_id, verify)
    LOGGER.info("Airlock request has been approved")

    # Check that deletion for user resource has started
    user_resource = await get_resource(f"/api{user_resource_path}", import_workspace_owner_token, verify)
    assert user_resource["userResource"]["deploymentStatus"] == "updating"
    LOGGER.info("Review VM has started deletion successfully")

    # EXPORT FLOW
