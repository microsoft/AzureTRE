import logging
from typing import Optional

import azure.functions as func
import datetime
import os
import uuid
import json
import requests

from exceptions import NoFilesInRequestException, TooManyFilesInRequestException

from shared_code import blob_operations, constants
from pydantic import BaseModel, parse_obj_as


class RequestProperties(BaseModel):
    request_id: str
    new_status: str
    previous_status: Optional[str]
    type: str
    workspace_id: str


def extract_properties(msg: func.ServiceBusMessage) -> RequestProperties:
    try:
        body = msg.get_body().decode('utf-8')
        logging.info('Python ServiceBus queue trigger processed message: %s', body)
        json_body = json.loads(body)
        result = parse_obj_as(RequestProperties, json_body["data"])
        if not result:
            raise Exception("Failed parsing request properties")

    return result


def main(msg: func.ServiceBusMessage):
    try:
        request_properties = extract_properties(msg)
        handle_status_changed(request_properties)


def handle_status_changed(request_properties: RequestProperties):
    new_status = request_properties.new_status
    req_id = request_properties.request_id
    workspace_id = request_properties.workspace_id
    request_type = request_properties.type

    logging.info('Processing request with id %s. new status is "%s", type is "%s"', req_id, new_status, request_type)


    logging.info('Calling some kind of API on workspace just to see if things work')
    # TODO: hardcoded API endpoint here
    response = requests.get(f'https://tred2483a0a.westeurope.cloudapp.azure.com/api/workspaces/{workspace_id}/requests/', auth=())
    return


# def get_credential() -> DefaultAzureCredential:
#     # TODO: have a config similar to the one in api_app?
#     managed_identity_client_id = os.environ.get("MANAGED_IDENTITY_CLIENT_ID")
#     if not managed_identity_client_id:
#         raise Exception("MANAGED_IDENTITY_CLIENT_ID is not set")

#     logging.info("using the Airlock processor's managed identity to get credentials.")
#     return DefaultAzureCredential(managed_identity_client_id=managed_identity_client_id,
#                                   exclude_shared_token_cache_credential=True)


async def get_workspace_auth_details(admin_token, workspace_id, verify) -> Tuple[str, str]:
    async with AsyncClient(verify=verify) as client:
        auth_headers = get_auth_header(admin_token)
        scope_uri = await get_identifier_uri(client, workspace_id, auth_headers)

        if config.TEST_ACCOUNT_CLIENT_ID != "" and config.TEST_ACCOUNT_CLIENT_SECRET != "":
            # Logging in as an Enterprise Application: Use Client Credentials flow
            payload = f"grant_type=client_credentials&client_id={config.TEST_ACCOUNT_CLIENT_ID}&client_secret={config.TEST_ACCOUNT_CLIENT_SECRET}&scope={scope_uri}/.default"
            url = f"https://login.microsoftonline.com/{config.AAD_TENANT_ID}/oauth2/v2.0/token"

        else:
            # Logging in as a User: Use Resource Owner Password Credentials flow
            payload = f"grant_type=password&resource={workspace_id}&username={config.TEST_USER_NAME}&password={config.TEST_USER_PASSWORD}&scope={scope_uri}/user_impersonation&client_id={config.TEST_APP_ID}"
            url = f"https://login.microsoftonline.com/{config.AAD_TENANT_ID}/oauth2/token"

        response = await client.post(url, headers=auth_headers, content=payload)
        try:
            responseJson = response.json()
        except JSONDecodeError:
            raise Exception("Failed to parse response as JSON: {}".format(response.content))

        if "access_token" not in responseJson or response.status_code != status.HTTP_200_OK:
            raise Exception("Failed to get access_token: {}".format(response.content))

        return responseJson["access_token"], scope_uri


async def get_identifier_uri(client, workspace_id: str, auth_headers) -> str:
    workspace = await get_workspace(client, workspace_id, auth_headers)

    if ("properties" not in workspace):
        raise Exception("Properties not found in workspace.")

    if ("scope_id" not in workspace["properties"]):
        raise Exception("Scope Id not found in workspace properties.")

    # Cope with the fact that scope id can have api:// at the front.
    return f"api://{workspace['properties']['scope_id'].replace('api://','')}"

async def get_workspace(client, workspace_id: str, headers) -> dict:
    full_endpoint = get_full_endpoint(f"/api/workspaces/{workspace_id}")

    response = await client.get(full_endpoint, headers=headers, timeout=TIMEOUT)
    if response.status_code == 200:
        return response.json()["workspace"]
    else:
        LOGGER.error(f"Non 200 response in get_workspace: {response.status_code}")
        LOGGER.error(f"Full response: {response}")
        raise Exception("Non 200 response in get_workspace")


def get_full_endpoint(endpoint: str) -> str:
    if (config.TRE_URL != ""):
        return f"{config.TRE_URL}{endpoint}"
    else:
        return f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{endpoint}"


def get_token():
    managed_identity = ManagedIdentityCredential(client_id=os.environ.get("MANAGED_IDENTITY_CLIENT_ID"))
    token = managed_identity.get_token(scopes=)
