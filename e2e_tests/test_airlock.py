import os
import pytest
import asyncio
import logging

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import ContainerClient

from airlock.request import post_request, get_request, upload_blob_using_sas, wait_for_status
from resources.resource import get_resource, post_resource
from resources.workspace import get_workspace_auth_details
from airlock import strings as airlock_strings
from e2e_tests.conftest import get_workspace_owner_token
from helpers import get_admin_token


pytestmark = pytest.mark.asyncio(loop_scope="session")
LOGGER = logging.getLogger(__name__)
BLOB_FILE_PATH = "./test_airlock_sample.txt"
BLOB_NAME = os.path.basename(BLOB_FILE_PATH)


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
    # We can't test teh export flow as we can't fully create an export request without special networking setup


@pytest.mark.airlock
@pytest.mark.extended
@pytest.mark.timeout(35 * 60)
async def test_airlock_flow(setup_test_workspace, verify) -> None:
    # 1. Get the workspace set up
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    # 2. create and submit airlock request
    request_id, container_url = await submit_airlock_import_request(workspace_path, workspace_owner_token, verify)

    # 3. approve request
    LOGGER.info("Approving airlock request")
    payload = {
        "approval": "True",
        "decisionExplanation": "the reason why this request was approved/rejected"
    }
    request_result = await post_request(payload, f'/api{workspace_path}/requests/{request_id}/review', workspace_owner_token, verify, 200)
    assert request_result["airlockRequest"]["reviews"][0]["decisionExplanation"] == "the reason why this request was approved/rejected"

    await wait_for_status(airlock_strings.APPROVED_STATUS, workspace_owner_token, workspace_path, request_id, verify)

    # 4. check the file has been deleted from the source
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

    # 5. get a link to the blob in the approved location.
    # For a full E2E we should try to download it, but can't without special networking setup.
    # So at the very least we check that we get the link for it.
    request_result = await get_request(f'/api{workspace_path}/requests/{request_id}/link', workspace_owner_token, verify, 200)
    container_url = request_result["containerUrl"]

    # 6. create airlock export request
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

    # 7. get container link
    LOGGER.info("Getting airlock request container URL")
    request_result = await get_request(f'/api{workspace_path}/requests/{request_id}/link', workspace_owner_token, verify, 200)
    container_url = request_result["containerUrl"]
    # we can't test any more the export flow since we don't have the network
    # access to upload the file from within the workspace.
