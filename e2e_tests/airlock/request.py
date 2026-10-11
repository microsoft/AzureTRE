import asyncio
import logging
from httpx import AsyncClient, Timeout
import os
import re
from urllib.parse import urlparse
from azure.storage.blob import BlobClient
from azure.storage.blob.aio import BlobClient as AsyncBlobClient
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError, ResourceExistsError
from uuid import UUID, uuid4
from airlock import strings
from e2e_tests.helpers import get_auth_header, get_full_endpoint

LOGGER = logging.getLogger(__name__)
TIMEOUT = Timeout(10, read=30)


async def post_request(payload, endpoint, access_token, verify, assert_status):
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        full_endpoint = get_full_endpoint(endpoint)
        auth_headers = get_auth_header(access_token)

        LOGGER.info(f"posting to {endpoint} with payload:\n{payload}")
        response = await client.post(full_endpoint, headers=auth_headers, json=payload, timeout=TIMEOUT)

        LOGGER.info(f"Response Status code: {response.status_code} Content: {response.content}")
        assert response.status_code == assert_status

        return response.json()


async def get_request(endpoint, access_token, verify, assert_status):
    """Return JSON on success or plain text for an expected HTTP error."""
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        full_endpoint = get_full_endpoint(endpoint)
        auth_headers = get_auth_header(access_token)
        auth_headers["accept"] = "application/json"

        response = await client.get(full_endpoint, headers=auth_headers, timeout=TIMEOUT)
        # Link responses contain a container SAS. Do not log response bodies because
        # doing so would expose credentials before the upload/delete helpers redact them.
        LOGGER.info(f"Response Status code: {response.status_code}")

        assert response.status_code == assert_status

        # The API's HTTP exception handler returns plain text for error responses.
        if response.is_error:
            return response.text

        return response.json()


async def upload_blob_using_sas(file_path: str, sas_url: str):
    async with AsyncClient(timeout=30.0) as client:
        parsed_sas_url = urlparse(sas_url)
        # Remove first / from path
        if parsed_sas_url.path[0] == "/":
            container_name = parsed_sas_url.path[1:]
        else:
            container_name = parsed_sas_url.path

        storage_account_url = f"{parsed_sas_url.scheme}://{parsed_sas_url.netloc}/"

        file_name = os.path.basename(file_path)
        _, file_ext = os.path.splitext(file_name)

        blob_url = f"{storage_account_url}{container_name}/{file_name}?{parsed_sas_url.query}"
        LOGGER.info(f"uploading [{file_name}] to container [{storage_account_url}{container_name}]")

        client = BlobClient.from_blob_url(blob_url)
        with open(file_name, "rb") as data:
            response = client.upload_blob(data)

        return response


async def delete_blob_using_sas(file_path: str, sas_url: str):
    parsed_sas_url = urlparse(sas_url)
    container_name = parsed_sas_url.path.lstrip("/")
    storage_account_url = f"{parsed_sas_url.scheme}://{parsed_sas_url.netloc}/"
    file_name = os.path.basename(file_path)

    blob_url = f"{storage_account_url}{container_name}/{file_name}?{parsed_sas_url.query}"
    LOGGER.info(f"deleting [{file_name}] from container [{storage_account_url}{container_name}]")

    client = BlobClient.from_blob_url(blob_url)
    client.delete_blob()


def submitted_container_id(sas_url, subscription_id, tre_id, request_id):
    """Bind the ARM observation to this request and the configured v2 account."""
    subscription_id = str(UUID(subscription_id))
    request_id = str(UUID(request_id))
    if not re.fullmatch(r"[a-zA-Z0-9-]+", tre_id):
        raise ValueError("Invalid TRE ID for Airlock deletion validation")
    account = f"stalairlock{tre_id}".replace("-", "").lower()
    parsed = urlparse(sas_url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != f"{account}.blob.core.windows.net"
        or parsed.path != f"/{request_id}-draft"
        or not parsed.query
        or parsed.fragment
    ):
        raise ValueError("The draft SAS does not match the test request and configured v2 storage account")
    return (
        f"/subscriptions/{subscription_id}/resourceGroups/rg-{tre_id}"
        f"/providers/Microsoft.Storage/storageAccounts/{account}/blobServices/default/containers/{request_id}"
    )


async def wait_for_draft_container_deletion(sas_url: str, *, arm, container_id, workspace_id, timeout=60, interval=2):
    """Require a rejected write and independent ARM evidence of draft deletion."""
    started = asyncio.get_running_loop().time()
    parsed = urlparse(sas_url)
    # A new name and overwrite avoid mistaking BlobAlreadyExists for revoked access.
    blob_url = parsed._replace(path=f"{parsed.path.rstrip('/')}/revocation-probe-{uuid4().hex}").geturl()
    async with AsyncBlobClient.from_blob_url(blob_url, retry_total=0, connection_timeout=5, read_timeout=10) as client:
        try:
            async with asyncio.timeout(timeout):
                while True:
                    try:
                        await client.upload_blob(b"post-submission draft probe", overwrite=True)
                    except ResourceNotFoundError as error:
                        if getattr(error, "error_code", None) != "ContainerNotFound":
                            raise
                        denied = True
                    except ResourceExistsError as error:
                        # Azure can reject writes while deletion is still in progress.
                        if getattr(error, "error_code", None) != "ContainerBeingDeleted":
                            raise
                        denied = False
                    except HttpResponseError as error:
                        # ABAC can deny a SAS operation when deleted container metadata
                        # is unavailable. This error alone does not prove deletion.
                        if (
                            error.status_code != 403
                            or getattr(error, "error_code", None) != "AuthorizationPermissionMismatch"
                        ):
                            raise
                        denied = True
                    else:
                        denied = False
                    if denied:
                        draft = await arm.request("GET", f"{container_id}-draft", "2023-05-01", missing_ok=True)
                        if draft is None:
                            # A live sibling in the same account prevents an incorrect
                            # subscription, missing account or failed lookup from passing.
                            submitted = await arm.request("GET", container_id, "2023-05-01")
                            metadata = submitted.get("properties", {}).get("metadata", {})
                            assert submitted.get("id", "").lower() == container_id.lower(), (
                                "ARM returned a different submitted container"
                            )
                            assert metadata.get("workspace_id") == workspace_id, (
                                "Submitted container belongs to a different workspace"
                            )
                            assert metadata.get("request_type") == "import", "Submitted container is not an import"
                            assert metadata.get("stage") == "import-in-progress", (
                                "Submitted container has an unexpected stage"
                            )
                            LOGGER.info(
                                "Draft write rejected and ARM deletion confirmed after %.1f seconds",
                                asyncio.get_running_loop().time() - started,
                            )
                            return
                    await asyncio.sleep(interval)
        except TimeoutError:
            raise AssertionError(f"Draft container deletion was not confirmed within {timeout} seconds") from None


async def wait_for_status(request_status: str, workspace_owner_token, workspace_path, request_id, verify):

    while True:
        request_result = await get_request(
            f"/api{workspace_path}/requests/{request_id}",
            workspace_owner_token,
            verify,
            200,
        )
        current_status = request_result[strings.AIRLOCK_REQUEST][strings.AIRLOCK_REQUEST_STATUS]

        if current_status == request_status:
            break

        if is_final_status(current_status):
            status = request_result[strings.AIRLOCK_REQUEST].get(strings.AIRLOCK_REQUEST_STATUS_MESSAGE)
            LOGGER.error(f"Airlock request ended with unexpected status: {current_status}. reason: {status}")
            raise Exception("Airlock request unexpected status.")

        LOGGER.info(f"Waiting for request status: {request_status}, current status is {current_status}")
        await asyncio.sleep(5)


def is_final_status(status):
    return status in [
        strings.APPROVED_STATUS,
        strings.REJECTED_STATUS,
        strings.CANCELLED_STATUS,
        strings.BLOCKED_STATUS,
        strings.FAILED_STATUS,
    ]
