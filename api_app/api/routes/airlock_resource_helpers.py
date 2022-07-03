from datetime import datetime, timedelta
import logging

from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import generate_container_sas, ContainerSasPermissions
from fastapi import HTTPException
from starlette import status
from core import config
from azure.identity import DefaultAzureCredential
from db.repositories.airlock_reviews import AirlockReviewRepository
from models.domain.airlock_review import AirlockReview
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus
from event_grid.helpers import send_status_changed_event
from models.domain.authentication import User
from models.domain.workspace import Workspace

from resources import strings, constants


class RequestAccountDetails:
    account_name: str
    account_rg: str

    def __init__(self, account_name, account_rg):
        self.account_name = account_name
        self.account_rg = account_rg


async def save_and_publish_event_airlock_request(airlock_request: AirlockRequest, airlock_request_repo: AirlockRequestRepository, user: User):
    try:
        logging.debug(f"Saving airlock request item: {airlock_request.id}")
        airlock_request.user = user
        airlock_request.updatedWhen = get_timestamp()
        airlock_request_repo.save_item(airlock_request)
    except Exception as e:
        logging.error(f'Failed saving airlock request {airlock_request}: {e}')
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        logging.debug(f"Sending status changed event for airlock request item: {airlock_request.id}")
        await send_status_changed_event(airlock_request)
    except Exception as e:
        airlock_request_repo.delete_item(airlock_request.id)
        logging.error(f"Failed sending status_changed message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.EVENT_GRID_GENERAL_ERROR_MESSAGE)


async def update_status_and_publish_event_airlock_request(airlock_request: AirlockRequest, airlock_request_repo: AirlockRequestRepository, user: User, new_status: AirlockRequestStatus):
    try:
        logging.debug(f"Updating airlock request item: {airlock_request.id}")
        updated_airlock_request = airlock_request_repo.update_airlock_request_status(airlock_request, new_status, user)
    except Exception as e:
        logging.error(f'Failed updating airlock_request item {airlock_request}: {e}')
        # If the validation failed, the error was not related to the saving itself
        if e.status_code == 400:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_ILLEGAL_STATUS_CHANGE)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        logging.debug(f"Sending status changed event for airlock request item: {airlock_request.id}")
        await send_status_changed_event(updated_airlock_request)
        return updated_airlock_request
    except Exception as e:
        logging.error(f"Failed sending status_changed message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.EVENT_GRID_GENERAL_ERROR_MESSAGE)


async def save_airlock_review(airlock_review: AirlockReview, airlock_review_repo: AirlockReviewRepository, user: User):
    try:
        logging.debug(f"Saving airlock review item: {airlock_review.id}")
        airlock_review.user = user
        airlock_review.updatedWhen = get_timestamp()
        airlock_review_repo.save_item(airlock_review)
    except Exception as e:
        logging.error(f'Failed saving airlock request {airlock_review}: {e}')
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)


def get_storage_management_client():
    token_credential = DefaultAzureCredential(managed_identity_client_id=config.MANAGED_IDENTITY_CLIENT_ID,
                                              exclude_shared_token_cache_credential=True)
    return StorageManagementClient(credential=token_credential, subscription_id=config.SUBSCRIPTION_ID)


def get_account_and_rg_by_request(airlock_request: AirlockRequest, workspace: Workspace) -> RequestAccountDetails:
    tre_id = config.TRE_ID
    short_workspace_id = workspace.id[-4:]
    if airlock_request.requestType == constants.IMPORT_TYPE:
        if airlock_request.status == AirlockRequestStatus.Draft:
            return RequestAccountDetails(constants.STORAGE_ACCOUNT_NAME_IMPORT_EXTERNAL.format(tre_id),
                                         constants.CORE_RESOURCE_GROUP_NAME.format(tre_id))
        elif airlock_request.status == AirlockRequestStatus.Submitted:
            return RequestAccountDetails(constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS.format(tre_id),
                                         constants.CORE_RESOURCE_GROUP_NAME.format(tre_id))
        elif airlock_request.status == AirlockRequestStatus.InReview:
            return RequestAccountDetails(constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS.format(tre_id),
                                         constants.CORE_RESOURCE_GROUP_NAME.format(tre_id))
        elif airlock_request.status == AirlockRequestStatus.Approved:
            return RequestAccountDetails(constants.STORAGE_ACCOUNT_NAME_IMPORT_APPROVED.format(short_workspace_id),
                                         constants.WORKSPACE_RESOURCE_GROUP_NAME.format(tre_id, short_workspace_id))
        elif airlock_request.status == AirlockRequestStatus.Rejected:
            return RequestAccountDetails(constants.STORAGE_ACCOUNT_NAME_IMPORT_REJECTED.format(tre_id),
                                         constants.CORE_RESOURCE_GROUP_NAME.format(tre_id))
    else:
        if airlock_request.status == AirlockRequestStatus.Draft:
            return RequestAccountDetails(constants.STORAGE_ACCOUNT_NAME_EXPORT_INTERNAL.format(short_workspace_id),
                                         constants.WORKSPACE_RESOURCE_GROUP_NAME.format(tre_id, short_workspace_id))
        elif airlock_request.status in AirlockRequestStatus.Submitted:
            return RequestAccountDetails(constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS.format(short_workspace_id),
                                         constants.WORKSPACE_RESOURCE_GROUP_NAME.format(tre_id, short_workspace_id))
        elif airlock_request.status == AirlockRequestStatus.InReview:
            return RequestAccountDetails(constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS.format(short_workspace_id),
                                         constants.WORKSPACE_RESOURCE_GROUP_NAME.format(tre_id, short_workspace_id))
        elif airlock_request.status == AirlockRequestStatus.Approved:
            return RequestAccountDetails(constants.STORAGE_ACCOUNT_NAME_EXPORT_APPROVED.format(tre_id),
                                         constants.CORE_RESOURCE_GROUP_NAME.format(tre_id))
        elif airlock_request.status == AirlockRequestStatus.Rejected:
            return RequestAccountDetails(constants.STORAGE_ACCOUNT_NAME_EXPORT_REJECTED.format(short_workspace_id),
                                         constants.WORKSPACE_RESOURCE_GROUP_NAME.format(tre_id, short_workspace_id))


def validate_user_is_allowed_to_access_sa(user: User, airlock_request: AirlockRequest):
    if "WorkspaceResearcher" not in user.roles and airlock_request.status != AirlockRequestStatus.InReview:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.AIRLOCK_OWNER_UNAUTHORIZED_TO_SA)

    if "WorkspaceOwner" not in user.roles and airlock_request.status == AirlockRequestStatus.InReview:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.AIRLOCK_RESEARCHER_UNAUTHORIZED_TO_SA)
    return


def get_storage_account_key(storage_client: StorageManagementClient, request_account_details: RequestAccountDetails):
    return storage_client.storage_accounts.list_keys(request_account_details.account_rg,
                                                     request_account_details.account_name).keys[0].value


def get_required_permission(airlock_request: AirlockRequest) -> ContainerSasPermissions:
    if airlock_request.status == AirlockRequestStatus.Draft:
        return ContainerSasPermissions(read=True, write=True)
    else:
        return ContainerSasPermissions(read=True)


def get_airlock_request_container_sas_token(storage_client: StorageManagementClient,
                                            request_account_details: RequestAccountDetails,
                                            airlock_request: AirlockRequest):
    account_key = get_storage_account_key(storage_client, request_account_details)
    required_permission = get_required_permission(airlock_request)
    expiry = datetime.utcnow() + timedelta(hours=config.AIRLOCK_SAS_TOKEN_EXPIRY_PERIOD_IN_HOURS)

    token = generate_container_sas(container_name=airlock_request.id,
                                   account_name=request_account_details.account_name,
                                   account_key=account_key,
                                   permission=required_permission,
                                   expiry=expiry)

    return "https://{}.blob.core.windows.net/{}?{}"\
        .format(request_account_details.account_name, airlock_request.id, token)


def get_timestamp() -> float:
    return datetime.utcnow().timestamp()
