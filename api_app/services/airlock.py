from datetime import datetime, timedelta
from services.logging import logger

from azure.storage.blob import generate_container_sas, ContainerSasPermissions, BlobServiceClient
from fastapi import HTTPException, status
from core import config, credentials
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus, AirlockRequestType, AirlockReviewUserResource, AirlockReviewDecision, AirlockActions, AirlockFile, AirlockReview
from models.domain.authentication import User
from models.domain.workspace import Workspace
from models.domain.user_resource import UserResource
from models.domain.operation import Operation
from models.domain.resource import ResourceType
from models.domain.workspace_service import WorkspaceService
from models.schemas.airlock_request import AirlockReviewInCreate
from models.schemas.airlock_request import AirlockRequestWithAllowedUserActions
from models.schemas.resource import ResourcePatch
from typing import Tuple, List, Optional
from models.schemas.user_resource import UserResourceInCreate
from services.azure_resource_status import get_azure_resource_status
from services.authentication import get_access_service

from resources import strings, constants

from api.routes.resource_helpers import save_and_deploy_resource, send_uninstall_message, update_user_resource

from db.repositories.user_resources import UserResourceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.operations import OperationRepository
from db.repositories.airlock_requests import AirlockRequestRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources_history import ResourceHistoryRepository

from collections import defaultdict
from event_grid.event_sender import send_status_changed_event, send_airlock_notification_event

STORAGE_ENDPOINT = config.STORAGE_ENDPOINT_SUFFIX


def get_account_by_request(airlock_request: AirlockRequest, workspace: Workspace) -> str:
    tre_id = config.TRE_ID
    short_workspace_id = workspace.id[-4:]
    if airlock_request.type == constants.IMPORT_TYPE:
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
    allowed_roles = []

    if (airlock_request.status == AirlockRequestStatus.InReview):
        allowed_roles = ["AirlockManager", "WorkspaceOwner"]
    else:
        allowed_roles = ["WorkspaceResearcher", "WorkspaceOwner"]

    if not _user_has_one_of_roles(user=user, roles=allowed_roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.AIRLOCK_UNAUTHORIZED_TO_SA)

    return


def validate_request_status(airlock_request: AirlockRequest):
    if airlock_request.status in [AirlockRequestStatus.ApprovalInProgress,
                                  AirlockRequestStatus.RejectionInProgress,
                                  AirlockRequestStatus.BlockingInProgress]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_IN_PROGRESS)
    elif airlock_request.status in [AirlockRequestStatus.Cancelled, AirlockRequestStatus.Revoked]:
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
                                            credential=credentials.get_credential())

    start = datetime.utcnow() - timedelta(minutes=15)
    expiry = datetime.utcnow() + timedelta(hours=config.AIRLOCK_SAS_TOKEN_EXPIRY_PERIOD_IN_HOURS)

    try:
        udk = blob_service_client.get_user_delegation_key(key_start_time=start, key_expiry_time=expiry)
    except Exception:
        raise Exception(f"Failed getting user delegation key, has the API identity been granted 'Storage Blob Data Contributor' access to the storage account {account_name}?")

    required_permission = get_required_permission(airlock_request)

    token = generate_container_sas(container_name=airlock_request.id,
                                   account_name=account_name,
                                   user_delegation_key=udk,
                                   permission=required_permission,
                                   start=start,
                                   expiry=expiry)

    return "https://{}.blob.{}/{}?{}" \
        .format(account_name, STORAGE_ENDPOINT, airlock_request.id, token)


def get_account_url(account_name: str) -> str:
    return f"https://{account_name}.blob.{STORAGE_ENDPOINT}/"


async def review_airlock_request(airlock_review_input: AirlockReviewInCreate, airlock_request: AirlockRequest, user: User, workspace: Workspace,
                                 airlock_request_repo: AirlockRequestRepository, user_resource_repo: UserResourceRepository,
                                 workspace_service_repo, operation_repo: WorkspaceServiceRepository, resource_template_repo: ResourceTemplateRepository,
                                 resource_history_repo: ResourceHistoryRepository) -> AirlockRequest:
    airlock_review = airlock_request_repo.create_airlock_review_item(airlock_review_input, user)
    # Store review with new status in cosmos, and send status_changed event
    if airlock_review.reviewDecision.value == AirlockReviewDecision.Approved:
        review_status = AirlockRequestStatus.ApprovalInProgress
    elif airlock_review.reviewDecision.value == AirlockReviewDecision.Rejected:
        review_status = AirlockRequestStatus.RejectionInProgress

    updated_airlock_request = await update_and_publish_event_airlock_request(airlock_request=airlock_request,
                                                                             airlock_request_repo=airlock_request_repo, updated_by=user,
                                                                             workspace=workspace, new_status=review_status,
                                                                             airlock_review=airlock_review)

    # If there was a VM created for the request, clean it up as it will no longer be needed
    # In this request, we aren't returning the operations for clean up of VMs,
    # however the operations still will be saved in the DB and displayed on the UI as normal.
    _ = await delete_all_review_user_resources(
        airlock_request=airlock_request,
        user_resource_repo=user_resource_repo,
        workspace_service_repo=workspace_service_repo,
        resource_template_repo=resource_template_repo,
        operations_repo=operation_repo,
        resource_history_repo=resource_history_repo,
        user=user
    )

    return updated_airlock_request


def get_airlock_container_link(airlock_request: AirlockRequest, user, workspace):
    validate_user_allowed_to_access_storage_account(user, airlock_request)
    validate_request_status(airlock_request)
    account_name: str = get_account_by_request(airlock_request, workspace)
    return get_airlock_request_container_sas_token(account_name, airlock_request)


async def create_review_vm(airlock_request: AirlockRequest, user: User, workspace: Workspace, user_resource_repo: UserResourceRepository, workspace_service_repo: WorkspaceServiceRepository,
                           operation_repo: OperationRepository, airlock_request_repo: AirlockRequestRepository, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository) -> Tuple[UserResource, Operation]:
    if airlock_request.type == AirlockRequestType.Import:
        config = workspace.properties["airlock_review_config"]["import"]
        review_workspace_id = config["import_vm_workspace_id"]
        review_workspace_service_id = config["import_vm_workspace_service_id"]
        user_resource_template_name = config["import_vm_user_resource_template_name"]
    else:
        assert airlock_request.type == AirlockRequestType.Export
        config = workspace.properties["airlock_review_config"]["export"]
        review_workspace_id = workspace.id
        review_workspace_service_id = config["export_vm_workspace_service_id"]
        user_resource_template_name = config["export_vm_user_resource_template_name"]

    # Check whether the user already has a healthy VM deployed for the request
    resource_already_exists = user.id in airlock_request.reviewUserResources
    if resource_already_exists:
        existing_resource = airlock_request.reviewUserResources[user.id]
        existing_resource = await user_resource_repo.get_user_resource_by_id(workspace_id=existing_resource.workspaceId, service_id=existing_resource.workspaceServiceId, resource_id=existing_resource.userResourceId)
        logger.info("User already has an existing review resource")
        await _handle_existing_review_resource(existing_resource, user, user_resource_repo, workspace_service_repo, operation_repo, resource_template_repo, resource_history_repo)

    # Create the VM
    user_resource, operation = await _deploy_vm(airlock_request, user, workspace, review_workspace_id, review_workspace_service_id, user_resource_template_name, user_resource_repo, workspace_service_repo, operation_repo, resource_template_repo, resource_history_repo)

    # Update the Airlock Request with the information on the VM
    updated_resource = await update_and_publish_event_airlock_request(
        airlock_request,
        airlock_request_repo,
        user,
        workspace,
        review_user_resource=AirlockReviewUserResource(
            workspaceId=review_workspace_id,
            workspaceServiceId=review_workspace_service_id,
            userResourceId=user_resource.id
        ))

    logger.info(f"Airlock Request {updated_resource.id} updated to include {updated_resource.reviewUserResources}")
    return updated_resource, operation


async def _deploy_vm(airlock_request: AirlockRequest, user: User, workspace: Workspace, review_workspace_id: str, review_workspace_service_id: str, user_resource_template_name: str,
                     user_resource_repo: UserResourceRepository, workspace_service_repo: WorkspaceServiceRepository, operation_repo: OperationRepository,
                     resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository):
    logger.info(f"Creating review VM in workspace:{review_workspace_id} service:{review_workspace_service_id} using template:{user_resource_template_name}")
    workspace_service = await workspace_service_repo.get_workspace_service_by_id(workspace_id=review_workspace_id, service_id=review_workspace_service_id)
    airlock_request_sas_url = get_airlock_container_link(airlock_request, user, workspace)

    user_resource_create = UserResourceInCreate(
        templateName=user_resource_template_name,
        properties={
            "display_name": "Airlock Review VM",
            "description": f"{airlock_request.title} (ID {airlock_request.id})",
            "airlock_request_sas_url": airlock_request_sas_url
        }
    )

    user_resource, resource_template = await user_resource_repo.create_user_resource_item(
        user_resource_create, review_workspace_id, review_workspace_service_id, workspace_service.templateName, user.id, user.roles)

    operation = await save_and_deploy_resource(
        resource=user_resource,
        resource_repo=user_resource_repo,
        operations_repo=operation_repo,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user,
        resource_template=resource_template)

    return user_resource, operation


async def _handle_existing_review_resource(existing_resource: AirlockReviewUserResource, user: User, user_resource_repo: UserResourceRepository, workspace_service_repo: WorkspaceServiceRepository,
                                           operation_repo: OperationRepository, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository):
    # Is the existing resource enabled, deployed, and can we get its power state information
    if existing_resource.isEnabled and existing_resource.deploymentStatus == "deployed" and 'azure_resource_id' in existing_resource.properties:
        resource_status = get_azure_resource_status(existing_resource.properties['azure_resource_id'])
        if "powerState" in resource_status and resource_status["powerState"] == "VM running":
            logger.info("Existing review resource is enabled, in a succeeded state and running. Returning a conflict error.")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="A healthy review resource is already deployed for the current user. "
                                "You may only have a single review resource.")

    # If it wasn't healthy or running, we'll delete the existing resource if not already deleted, and then create a new one
    logger.info("Existing review resource is in an unhealthy state.")
    if existing_resource.deploymentStatus != "deleted":
        logger.info("Deleting existing user resource...")
        _ = await delete_review_user_resource(
            user_resource=existing_resource,
            user_resource_repo=user_resource_repo,
            workspace_service_repo=workspace_service_repo,
            resource_template_repo=resource_template_repo,
            operations_repo=operation_repo,
            resource_history_repo=resource_history_repo,
            user=user
        )


async def save_and_publish_event_airlock_request(airlock_request: AirlockRequest, airlock_request_repo: AirlockRequestRepository, user: User, workspace: Workspace):

    access_service = get_access_service()
    role_assignment_details = access_service.get_workspace_user_emails_by_role_assignment(workspace)
    if config.ENABLE_AIRLOCK_EMAIL_CHECK:
        check_email_exists(role_assignment_details)

    try:
        logger.debug(f"Saving airlock request item: {airlock_request.id}")
        airlock_request.updatedBy = user
        airlock_request.updatedWhen = get_timestamp()
        await airlock_request_repo.save_item(airlock_request)
    except Exception:
        logger.exception(f'Failed saving airlock request {airlock_request}')
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        logger.debug(f"Sending status changed event for airlock request item: {airlock_request.id}")
        await send_status_changed_event(airlock_request=airlock_request, previous_status=None)
        await send_airlock_notification_event(airlock_request, workspace, role_assignment_details)
    except Exception:
        await airlock_request_repo.delete_item(airlock_request.id)
        logger.exception("Failed sending status_changed message")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.EVENT_GRID_GENERAL_ERROR_MESSAGE)


async def update_and_publish_event_airlock_request(
        airlock_request: AirlockRequest,
        airlock_request_repo: AirlockRequestRepository,
        updated_by: User,
        workspace: Workspace,
        new_status: Optional[AirlockRequestStatus] = None,
        request_files: Optional[List[AirlockFile]] = None,
        status_message: Optional[str] = None,
        airlock_review: Optional[AirlockReview] = None,
        review_user_resource: Optional[AirlockReviewUserResource] = None) -> AirlockRequest:
    try:
        logger.debug(f"Updating airlock request item: {airlock_request.id}")
        updated_airlock_request = await airlock_request_repo.update_airlock_request(
            original_request=airlock_request,
            updated_by=updated_by,
            new_status=new_status,
            request_files=request_files,
            status_message=status_message,
            airlock_review=airlock_review,
            review_user_resource=review_user_resource)
    except Exception as e:
        logger.exception(f'Failed updating airlock_request item {airlock_request}')
        # If the validation failed, the error was not related to the saving itself
        if hasattr(e, 'status_code'):
            if e.status_code == 400:  # type: ignore
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_ILLEGAL_STATUS_CHANGE)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    if not new_status:
        logger.debug(f"Skipping sending 'status changed' event for airlock request item: {airlock_request.id} - there is no status change")
        return updated_airlock_request

    try:
        logger.debug(f"Sending status changed event for airlock request item: {airlock_request.id}")
        await send_status_changed_event(airlock_request=updated_airlock_request, previous_status=airlock_request.status)
        access_service = get_access_service()
        role_assignment_details = access_service.get_workspace_user_emails_by_role_assignment(workspace)
        await send_airlock_notification_event(updated_airlock_request, workspace, role_assignment_details)
        return updated_airlock_request
    except Exception:
        logger.exception("Failed sending status_changed message")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.EVENT_GRID_GENERAL_ERROR_MESSAGE)


def get_timestamp() -> float:
    return datetime.utcnow().timestamp()


def check_email_exists(role_assignment_details: defaultdict(list)):
    if not role_assignment_details.get("WorkspaceResearcher") and not role_assignment_details.get("WorkspaceOwner"):
        logger.error(strings.AIRLOCK_NO_EMAIL)
        raise HTTPException(status_code=status.HTTP_417_EXPECTATION_FAILED, detail=strings.AIRLOCK_NO_EMAIL)
    if not role_assignment_details.get("AirlockManager"):
        logger.error(strings.AIRLOCK_NO_AIRLOCK_MANAGER_EMAIL)
        raise HTTPException(status_code=status.HTTP_417_EXPECTATION_FAILED, detail=strings.AIRLOCK_NO_AIRLOCK_MANAGER_EMAIL)


async def get_airlock_requests_by_user_and_workspace(user: User, workspace: Workspace, airlock_request_repo: AirlockRequestRepository,
                                                     creator_user_id: Optional[str] = None, type: Optional[AirlockRequestType] = None, status: Optional[AirlockRequestStatus] = None,
                                                     order_by: Optional[str] = None, order_ascending=True) -> List[AirlockRequest]:
    return await airlock_request_repo.get_airlock_requests(workspace_id=workspace.id, creator_user_id=creator_user_id, type=type, status=status,
                                                           order_by=order_by, order_ascending=order_ascending)


def get_allowed_actions(request: AirlockRequest, user: User, airlock_request_repo: AirlockRequestRepository) -> AirlockRequestWithAllowedUserActions:
    allowed_actions = []

    can_review_request = airlock_request_repo.validate_status_update(request.status, AirlockRequestStatus.ApprovalInProgress)
    can_cancel_request = airlock_request_repo.validate_status_update(request.status, AirlockRequestStatus.Cancelled)
    can_submit_request = airlock_request_repo.validate_status_update(request.status, AirlockRequestStatus.Submitted)
    can_revoke_request = airlock_request_repo.validate_status_update(request.status, AirlockRequestStatus.Revoked)

    if can_review_request and "AirlockManager" in user.roles:
        allowed_actions.append(AirlockActions.Review)

    if can_cancel_request and ("WorkspaceOwner" in user.roles or "WorkspaceResearcher" in user.roles):
        allowed_actions.append(AirlockActions.Cancel)

    if can_submit_request and ("WorkspaceOwner" in user.roles or "WorkspaceResearcher" in user.roles):
        allowed_actions.append(AirlockActions.Submit)

    if can_revoke_request and "AirlockManager" in user.roles:
        allowed_actions.append(AirlockActions.Revoke)

    return allowed_actions


def enrich_requests_with_allowed_actions(requests: List[AirlockRequest], user: User, airlock_request_repo: AirlockRequestRepository) -> List[AirlockRequestWithAllowedUserActions]:
    enriched_requests = []
    for request in requests:
        allowed_actions = get_allowed_actions(request, user, airlock_request_repo)
        enriched_requests.append(AirlockRequestWithAllowedUserActions(airlockRequest=request, allowedUserActions=allowed_actions))
    return enriched_requests


async def delete_review_user_resource(
        user_resource: UserResource,
        user_resource_repo: UserResourceRepository,
        workspace_service_repo: WorkspaceServiceRepository,
        resource_template_repo: ResourceTemplateRepository,
        operations_repo: OperationRepository,
        resource_history_repo: ResourceHistoryRepository,
        user: User) -> Operation:
    workspace_service = await workspace_service_repo.get_workspace_service_by_id(workspace_id=user_resource.workspaceId,
                                                                                 service_id=user_resource.parentWorkspaceServiceId)

    # disable might contain logic that we need to execute before the deletion of the resource
    _ = await disable_user_resource(user_resource, user, workspace_service, user_resource_repo, resource_template_repo, operations_repo, resource_history_repo)

    logger.info(f"Deleting user resource {user_resource.id} in workspace service {workspace_service.id}")
    operation = await send_uninstall_message(
        resource=user_resource,
        resource_repo=user_resource_repo,
        operations_repo=operations_repo,
        resource_type=ResourceType.UserResource,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user)
    logger.info(f"Started operation {operation}")
    return operation


async def disable_user_resource(
        user_resource: UserResource,
        user: User,
        workspace_service: WorkspaceService,
        user_resource_repo: UserResourceRepository,
        resource_template_repo: ResourceTemplateRepository,
        operations_repo: OperationRepository,
        resource_history_repo: ResourceHistoryRepository) -> Operation:

    resource_patch = ResourcePatch(isEnabled=False)
    operation = await update_user_resource(user_resource=user_resource, resource_patch=resource_patch, force_version_update=False,
                                           user=user, etag=user_resource.etag, workspace_service=workspace_service, user_resource_repo=user_resource_repo,
                                           resource_template_repo=resource_template_repo, operations_repo=operations_repo, resource_history_repo=resource_history_repo)

    return operation


async def delete_all_review_user_resources(
        airlock_request: AirlockRequest,
        user_resource_repo: UserResourceRepository,
        workspace_service_repo: WorkspaceServiceRepository,
        resource_template_repo: ResourceTemplateRepository,
        operations_repo: OperationRepository,
        resource_history_repo: ResourceHistoryRepository,
        user: User) -> List[Operation]:
    operations: List[Operation] = []
    for review_ur in airlock_request.reviewUserResources.values():
        user_resource = await user_resource_repo.get_user_resource_by_id(
            workspace_id=review_ur.workspaceId,
            service_id=review_ur.workspaceServiceId,
            resource_id=review_ur.userResourceId
        )

        operation = await delete_review_user_resource(
            user_resource=user_resource,
            user_resource_repo=user_resource_repo,
            workspace_service_repo=workspace_service_repo,
            resource_template_repo=resource_template_repo,
            operations_repo=operations_repo,
            resource_history_repo=resource_history_repo,
            user=user
        )
        operations.append(operation)

    logger.info(f"Started {len(operations)} operations on deleting user resources")
    return operations


async def cancel_request(airlock_request: AirlockRequest, user: User, workspace: Workspace,
                         airlock_request_repo: AirlockRequestRepository, user_resource_repo: UserResourceRepository, workspace_service_repo: WorkspaceServiceRepository,
                         resource_template_repo: ResourceTemplateRepository, operations_repo: OperationRepository, resource_history_repo: ResourceHistoryRepository) -> AirlockRequest:
    updated_request = await update_and_publish_event_airlock_request(airlock_request=airlock_request, airlock_request_repo=airlock_request_repo, updated_by=user, workspace=workspace, new_status=AirlockRequestStatus.Cancelled)
    await delete_all_review_user_resources(airlock_request, user_resource_repo, workspace_service_repo, resource_template_repo, operations_repo, resource_history_repo, user)
    return updated_request


async def revoke_request(airlock_request: AirlockRequest, user: User, workspace: Workspace,
                         airlock_request_repo: AirlockRequestRepository, revocation_reason: str) -> AirlockRequest:
    """
    Revoke an approved airlock request. This prevents new download links from being generated.
    """
    # Create a review entry for the revocation
    revoke_review = airlock_request_repo.create_airlock_revoke_review_item(revocation_reason, user)

    updated_request = await update_and_publish_event_airlock_request(
        airlock_request=airlock_request,
        airlock_request_repo=airlock_request_repo,
        updated_by=user,
        workspace=workspace,
        new_status=AirlockRequestStatus.Revoked,
        airlock_review=revoke_review
    )
    return updated_request


def _user_has_one_of_roles(user: User, roles) -> bool:
    return any(role in roles for role in user.roles)
