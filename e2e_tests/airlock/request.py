import asyncio
import logging
from httpx import AsyncClient, Timeout
import os
from urllib.parse import urlparse
from azure.storage.blob import BlobClient
from airlock import strings
from e2e_tests.helpers import get_auth_header, get_full_endpoint

LOGGER = logging.getLogger(__name__)
TIMEOUT = Timeout(10, read=30)


async def post_request(payload, endpoint, access_token, verify, assert_status):
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:

        full_endpoint = get_full_endpoint(endpoint)
        auth_headers = get_auth_header(access_token)

        LOGGER.info(f"posting to {endpoint} with payload:\n{payload}")
        response = await client.post(
            full_endpoint, headers=auth_headers, json=payload, timeout=TIMEOUT
        )

        LOGGER.info(
            f"Response Status code: {response.status_code} Content: {response.content}"
        )
        assert response.status_code == assert_status

        return response.json()


async def get_request(endpoint, access_token, verify, assert_status):
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:

        full_endpoint = get_full_endpoint(endpoint)
        auth_headers = get_auth_header(access_token)
        auth_headers["accept"] = "application/json"

        response = await client.get(
            full_endpoint, headers=auth_headers, timeout=TIMEOUT
        )
        LOGGER.info(
            f"Response Status code: {response.status_code} Content: {response.content}"
        )

        assert response.status_code == assert_status

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
        LOGGER.info(f"uploading [{file_name}] to container [{blob_url}]")

        client = BlobClient.from_blob_url(blob_url)
        with open(file_name, 'rb') as data:
            response = client.upload_blob(data)

        return response


async def wait_for_status(
    request_status: str, workspace_owner_token, workspace_path, request_id, verify
):

    while True:
        request_result = await get_request(
            f"/api{workspace_path}/requests/{request_id}",
            workspace_owner_token,
            verify,
            200,
        )
        current_status = request_result[strings.AIRLOCK_REQUEST][strings.AIRLOCK_REQUEST_STATUS]

        if (current_status == request_status):
            break

        if (is_final_status(current_status)):
            status = request_result[strings.AIRLOCK_REQUEST].get(strings.AIRLOCK_REQUEST_STATUS_MESSAGE)
            LOGGER.error(f"Airlock request ended with unexpected status: {current_status}. reason: {status}")
            raise Exception("Airlock request unexpected status.")

        LOGGER.info(f"Waiting for request status: {request_status}, current status is {current_status}")
        await asyncio.sleep(5)


def is_final_status(status):
    return status in [strings.APPROVED_STATUS, strings.REJECTED_STATUS, strings.CANCELLED_STATUS, strings.BLOCKED_STATUS, strings.FAILED_STATUS]
