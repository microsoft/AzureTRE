import logging
from datetime import datetime, timedelta

from azure.storage.blob import generate_container_sas, ContainerSasPermissions, BlobServiceClient
from fastapi import HTTPException
from starlette import status
from core import config
from azure.identity import DefaultAzureCredential
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus
from models.domain.authentication import User
from models.domain.workspace import Workspace

from resources import strings, constants


def get_credential() -> DefaultAzureCredential:
    managed_identity = config.MANAGED_IDENTITY_CLIENT_ID
    if managed_identity:
        logging.info("Using managed identity credentials.")
    return DefaultAzureCredential(managed_identity_client_id=config.MANAGED_IDENTITY_CLIENT_ID,
                                  exclude_shared_token_cache_credential=True) if managed_identity else DefaultAzureCredential()


def get_account_by_request(airlock_request: AirlockRequest, workspace: Workspace) -> str:
    tre_id = config.TRE_ID
    short_workspace_id = workspace.id[-4:]
    if airlock_request.requestType == constants.IMPORT_TYPE:
        if airlock_request.status == AirlockRequestStatus.Draft:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_EXTERNAL.format(tre_id)
        elif airlock_request.status == AirlockRequestStatus.Submitted:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS.format(tre_id)
        elif airlock_request.status == AirlockRequestStatus.InReview:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS.format(tre_id)
        elif airlock_request.status == AirlockRequestStatus.Approved:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_APPROVED.format(short_workspace_id)
        elif airlock_request.status == AirlockRequestStatus.Rejected:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_REJECTED.format(tre_id)
        elif airlock_request.status == AirlockRequestStatus.Blocked:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_BLOCKED.format(tre_id)
    else:
        if airlock_request.status == AirlockRequestStatus.Draft:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_INTERNAL.format(short_workspace_id)
        elif airlock_request.status in AirlockRequestStatus.Submitted:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS.format(short_workspace_id)
        elif airlock_request.status == AirlockRequestStatus.InReview:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS.format(short_workspace_id)
        elif airlock_request.status == AirlockRequestStatus.Approved:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_APPROVED.format(tre_id)
        elif airlock_request.status == AirlockRequestStatus.Rejected:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_REJECTED.format(short_workspace_id)
        elif airlock_request.status == AirlockRequestStatus.Blocked:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_BLOCKED.format(short_workspace_id)


def validate_user_allowed_to_access_storage_account(user: User, airlock_request: AirlockRequest):
    if "WorkspaceResearcher" not in user.roles and airlock_request.status != AirlockRequestStatus.InReview:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.AIRLOCK_UNAUTHORIZED_TO_SA)

    if "WorkspaceOwner" not in user.roles and airlock_request.status == AirlockRequestStatus.InReview:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.AIRLOCK_UNAUTHORIZED_TO_SA)
    return


def validate_request_status(airlock_request: AirlockRequest):
    if airlock_request.status in [AirlockRequestStatus.ApprovalInProgress,
                                  AirlockRequestStatus.RejectionInProgress,
                                  AirlockRequestStatus.BlockingInProgress]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_IN_PROGRESS)
    elif airlock_request.status == AirlockRequestStatus.Cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_IS_CANCELED)
    elif airlock_request.status in [AirlockRequestStatus.Failed,
                                    AirlockRequestStatus.Rejected,
                                    AirlockRequestStatus.Blocked]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_UNACCESSIBLE)
    else:
        return


def get_required_permission(airlock_request: AirlockRequest) -> ContainerSasPermissions:
    if airlock_request.status == AirlockRequestStatus.Draft:
        return ContainerSasPermissions(read=True, write=True, list=True, delete=True)
    else:
        return ContainerSasPermissions(read=True, list=True)


def get_airlock_request_container_sas_token(account_name: str,
                                            airlock_request: AirlockRequest):
    blob_service_client = BlobServiceClient(account_url=get_account_url(account_name),
                                            credential=get_credential())
    expiry = datetime.utcnow() + timedelta(hours=config.AIRLOCK_SAS_TOKEN_EXPIRY_PERIOD_IN_HOURS)
    udk = blob_service_client.get_user_delegation_key(datetime.utcnow(), expiry)
    required_permission = get_required_permission(airlock_request)

    token = generate_container_sas(container_name=airlock_request.id,
                                   account_name=account_name,
                                   user_delegation_key=udk,
                                   permission=required_permission,
                                   expiry=expiry)

    return "https://{}.blob.core.windows.net/{}?{}" \
        .format(account_name, airlock_request.id, token)


def get_account_url(account_name: str) -> str:
    return f"https://{account_name}.blob.core.windows.net/"
