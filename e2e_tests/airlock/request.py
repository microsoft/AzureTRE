import asyncio
import logging
from httpx import AsyncClient, Timeout
from e2e_tests.helpers import get_auth_header, get_full_endpoint
import os
from urllib.parse import urlparse
import mimetypes
import requests
from azure.storage.blob import ContentSettings

LOGGER = logging.getLogger(__name__)
TIMEOUT = Timeout(10, read=30)


async def post_request(payload, endpoint, access_token, verify, assert_status):
    async with AsyncClient(verify=verify, timeout=30.0) as client:

        full_endpoint = get_full_endpoint(endpoint)
        auth_headers = get_auth_header(access_token)

        LOGGER.info(f'posting to {endpoint} with payload:\n{payload}')
        response = await client.post(full_endpoint, headers=auth_headers, json=payload, timeout=TIMEOUT)

        LOGGER.info(f'Response Status code: {response.status_code} Content: {response.content}')
        assert response.status_code == assert_status

        return response.json()


async def get_request(endpoint, access_token, verify, assert_status):
    async with AsyncClient(verify=verify, timeout=30.0) as client:

        full_endpoint = get_full_endpoint(endpoint)
        auth_headers = get_auth_header(access_token)
        auth_headers["accept"] = "application/json"

        response = await client.get(full_endpoint, headers=auth_headers, timeout=TIMEOUT)
        LOGGER.info(f'Response Status code: {response.status_code} Content: {response.content}')

        assert response.status_code == assert_status

        return response.json()


def upload_blob_using_sas(file_path: str, sas_url: str):
    parsed_sas_url = urlparse(sas_url)
    # Remove first / from path
    if parsed_sas_url.path[0] == "/":
        container_name = parsed_sas_url.path[1:]
    else:
        container_name = parsed_sas_url.path

    storage_account_url = f"{parsed_sas_url.scheme}://{parsed_sas_url.netloc}/"

    file_name = os.path.basename(file_path)
    _, file_ext = os.path.splitext(file_name)

    with open(file_path, "rb") as fh:
        headers = {"x-ms-blob-type": "BlockBlob"}
        if file_ext != "":
            headers["content-type"] = ContentSettings(content_type=mimetypes.types_map[file_ext]).content_type

        response = requests.put(
            f"{storage_account_url}{container_name}/{file_name}?{parsed_sas_url.query}",
            data=fh,
            headers=headers,
            params={"file": file_name},
        )
        return response.status_code


async def wait_for_status(request_status: str, workspace_owner_token, workspace_path, request_id, verify):

    finised = False
    while not finised:
        LOGGER.info(f'Waiting for request status: {request_status}')
        await asyncio.sleep(2)

        request_result = await get_request(f'/api{workspace_path}/requests/{request_id}', workspace_owner_token, verify, 200)
        finised = request_result["airlockRequest"]["status"] == request_status
