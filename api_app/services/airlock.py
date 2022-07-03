from datetime import datetime, timedelta

from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import generate_container_sas, ContainerSasPermissions
from fastapi import HTTPException
from starlette import status

from api.routes.airlock_resource_helpers import RequestAccountDetails
from core import config
from azure.identity import DefaultAzureCredential
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus
from models.domain.authentication import User
from models.domain.workspace import Workspace

from resources import strings, constants


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
