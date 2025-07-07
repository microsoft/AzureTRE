from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status as status_code, Response

from jsonschema.exceptions import ValidationError
from api.helpers import get_repository
from db.repositories.resources_history import ResourceHistoryRepository
from db.repositories.user_resources import UserResourceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.operations import OperationRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.airlock_requests import AirlockRequestRepository
from db.errors import EntityDoesNotExist, UserNotAuthorizedToUseTemplate

from api.dependencies.workspaces import get_workspace_by_id_from_path, get_deployed_workspace_by_id_from_path
from api.dependencies.airlock import get_airlock_request_by_id_from_path
from models.domain.airlock_request import AirlockRequestStatus, AirlockRequestType
from models.schemas.airlock_request_url import AirlockRequestTokenInResponse
from models.schemas.airlock_request import AirlockRequestAndOperationInResponse, AirlockRequestInCreate, AirlockRequestWithAllowedUserActions, \
    AirlockRequestWithAllowedUserActionsInList, AirlockReviewInCreate, AirlockRevokeInCreate
from resources import strings
from services.authentication import get_current_workspace_owner_or_researcher_user_or_airlock_manager, \
    get_current_workspace_owner_or_researcher_user, get_current_airlock_manager_user

from .resource_helpers import construct_location_header

from services.airlock import create_review_vm, review_airlock_request, get_airlock_container_link, get_allowed_actions, save_and_publish_event_airlock_request, update_and_publish_event_airlock_request, \
    enrich_requests_with_allowed_actions, get_airlock_requests_by_user_and_workspace, cancel_request, revoke_request
from services.logging import logger

airlock_workspace_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager)])


# airlock
@airlock_workspace_router.post("/workspaces/{workspace_id}/requests", status_code=status_code.HTTP_201_CREATED,
                               response_model=AirlockRequestWithAllowedUserActions, name=strings.API_CREATE_AIRLOCK_REQUEST,
                               dependencies=[Depends(get_current_workspace_owner_or_researcher_user), Depends(get_workspace_by_id_from_path)])
async def create_draft_request(airlock_request_input: AirlockRequestInCreate, user=Depends(get_current_workspace_owner_or_researcher_user),
                               airlock_request_repo=Depends(get_repository(AirlockRequestRepository)),
                               workspace=Depends(get_deployed_workspace_by_id_from_path)) -> AirlockRequestWithAllowedUserActions:
    if workspace.properties.get("enable_airlock") is False:
        raise HTTPException(status_code=status_code.HTTP_405_METHOD_NOT_ALLOWED, detail=strings.AIRLOCK_NOT_ENABLED_IN_WORKSPACE)
    try:
        airlock_request = airlock_request_repo.create_airlock_request_item(airlock_request_input, workspace.id, user)
        await save_and_publish_event_airlock_request(airlock_request, airlock_request_repo, user, workspace)
        allowed_actions = get_allowed_actions(airlock_request, user, airlock_request_repo)
        return AirlockRequestWithAllowedUserActions(airlockRequest=airlock_request, allowedUserActions=allowed_actions)
    except (ValidationError, ValueError) as e:
        logger.exception("Failed creating airlock request model instance")
        raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST, detail=str(e))


@airlock_workspace_router.get("/workspaces/{workspace_id}/requests",
                              status_code=status_code.HTTP_200_OK,
                              response_model=AirlockRequestWithAllowedUserActionsInList,
                              name=strings.API_LIST_AIRLOCK_REQUESTS,
                              dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager),
                                            Depends(get_workspace_by_id_from_path)])
async def get_all_airlock_requests_by_workspace(
        airlock_request_repo=Depends(get_repository(AirlockRequestRepository)),
        workspace=Depends(get_deployed_workspace_by_id_from_path),
        user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager),
        creator_user_id: Optional[str] = None, type: Optional[AirlockRequestType] = None, status: Optional[AirlockRequestStatus] = None,
        order_by: Optional[str] = None, order_ascending: bool = True) -> AirlockRequestWithAllowedUserActionsInList:
    try:
        airlock_requests = await get_airlock_requests_by_user_and_workspace(user=user, workspace=workspace, airlock_request_repo=airlock_request_repo,
                                                                            creator_user_id=creator_user_id, type=type, status=status,
                                                                            order_by=order_by, order_ascending=order_ascending)
        airlock_requests_with_allowed_user_actions = enrich_requests_with_allowed_actions(airlock_requests, user, airlock_request_repo)
        return AirlockRequestWithAllowedUserActionsInList(airlockRequests=airlock_requests_with_allowed_user_actions)
    except (ValidationError, ValueError) as e:
        logger.exception("Failed retrieving all the airlock requests for a workspace")
        raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST, detail=str(e))


@airlock_workspace_router.get("/workspaces/{workspace_id}/requests/{airlock_request_id}", status_code=status_code.HTTP_200_OK,
                              response_model=AirlockRequestWithAllowedUserActions, name=strings.API_GET_AIRLOCK_REQUEST,
                              dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager), Depends(get_workspace_by_id_from_path)])
async def retrieve_airlock_request_by_id(airlock_request=Depends(get_airlock_request_by_id_from_path),
                                         airlock_request_repo=Depends(get_repository(AirlockRequestRepository)),
                                         user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager)) -> AirlockRequestWithAllowedUserActions:
    allowed_actions = get_allowed_actions(airlock_request, user, airlock_request_repo)
    return AirlockRequestWithAllowedUserActions(airlockRequest=airlock_request, allowedUserActions=allowed_actions)


@airlock_workspace_router.post("/workspaces/{workspace_id}/requests/{airlock_request_id}/submit", status_code=status_code.HTTP_200_OK,
                               response_model=AirlockRequestWithAllowedUserActions, name=strings.API_SUBMIT_AIRLOCK_REQUEST,
                               dependencies=[Depends(get_current_workspace_owner_or_researcher_user), Depends(get_workspace_by_id_from_path)])
async def create_submit_request(airlock_request=Depends(get_airlock_request_by_id_from_path),
                                user=Depends(get_current_workspace_owner_or_researcher_user),
                                airlock_request_repo=Depends(get_repository(AirlockRequestRepository)),
                                workspace=Depends(get_workspace_by_id_from_path)) -> AirlockRequestWithAllowedUserActions:
    updated_request = await update_and_publish_event_airlock_request(airlock_request, airlock_request_repo, user, workspace,
                                                                     new_status=AirlockRequestStatus.Submitted)
    allowed_actions = get_allowed_actions(updated_request, user, airlock_request_repo)
    return AirlockRequestWithAllowedUserActions(airlockRequest=updated_request, allowedUserActions=allowed_actions)


@airlock_workspace_router.post("/workspaces/{workspace_id}/requests/{airlock_request_id}/cancel", status_code=status_code.HTTP_200_OK,
                               response_model=AirlockRequestWithAllowedUserActions, name=strings.API_CANCEL_AIRLOCK_REQUEST,
                               dependencies=[Depends(get_current_workspace_owner_or_researcher_user), Depends(get_workspace_by_id_from_path)])
async def create_cancel_request(airlock_request=Depends(get_airlock_request_by_id_from_path),
                                user=Depends(get_current_workspace_owner_or_researcher_user),
                                workspace=Depends(get_workspace_by_id_from_path),
                                airlock_request_repo=Depends(get_repository(AirlockRequestRepository)),
                                user_resource_repo=Depends(get_repository(UserResourceRepository)),
                                workspace_service_repo=Depends(get_repository(WorkspaceServiceRepository)),
                                resource_history_repo=Depends(get_repository(ResourceHistoryRepository)),
                                operation_repo=Depends(get_repository(OperationRepository)),
                                resource_template_repo=Depends(get_repository(ResourceTemplateRepository)),) -> AirlockRequestWithAllowedUserActions:
    updated_request = await cancel_request(airlock_request, user, workspace, airlock_request_repo, user_resource_repo, workspace_service_repo, resource_template_repo, operation_repo, resource_history_repo)
    allowed_actions = get_allowed_actions(updated_request, user, airlock_request_repo)
    return AirlockRequestWithAllowedUserActions(airlockRequest=updated_request, allowedUserActions=allowed_actions)


@airlock_workspace_router.post("/workspaces/{workspace_id}/requests/{airlock_request_id}/revoke", status_code=status_code.HTTP_200_OK,
                               response_model=AirlockRequestWithAllowedUserActions, name=strings.API_REVOKE_AIRLOCK_REQUEST,
                               dependencies=[Depends(get_current_airlock_manager_user), Depends(get_workspace_by_id_from_path)])
async def create_revoke_request(revoke_input: AirlockRevokeInCreate,
                                airlock_request=Depends(get_airlock_request_by_id_from_path),
                                user=Depends(get_current_airlock_manager_user),
                                workspace=Depends(get_workspace_by_id_from_path),
                                airlock_request_repo=Depends(get_repository(AirlockRequestRepository))) -> AirlockRequestWithAllowedUserActions:
    updated_request = await revoke_request(airlock_request, user, workspace, airlock_request_repo, revoke_input.reason)
    allowed_actions = get_allowed_actions(updated_request, user, airlock_request_repo)
    return AirlockRequestWithAllowedUserActions(airlockRequest=updated_request, allowedUserActions=allowed_actions)


@airlock_workspace_router.post("/workspaces/{workspace_id}/requests/{airlock_request_id}/review-user-resource",
                               status_code=status_code.HTTP_202_ACCEPTED, response_model=AirlockRequestAndOperationInResponse,
                               name=strings.API_CREATE_AIRLOCK_REVIEW_USER_RESOURCE,
                               dependencies=[Depends(get_current_airlock_manager_user), Depends(get_workspace_by_id_from_path)])
async def create_review_user_resource(
        response: Response,
        airlock_request=Depends(get_airlock_request_by_id_from_path),
        user=Depends(get_current_airlock_manager_user),
        workspace=Depends(get_deployed_workspace_by_id_from_path),
        user_resource_repo=Depends(get_repository(UserResourceRepository)),
        workspace_service_repo=Depends(get_repository(WorkspaceServiceRepository)),
        operation_repo=Depends(get_repository(OperationRepository)),
        airlock_request_repo=Depends(get_repository(AirlockRequestRepository)),
        resource_template_repo=Depends(get_repository(ResourceTemplateRepository)),
        resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> AirlockRequestAndOperationInResponse:

    if airlock_request.status != AirlockRequestStatus.InReview:
        raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST,
                            detail="Airlock request must be in 'in_review' status to create a Review User Resource")
    try:
        updated_resource, operation = await create_review_vm(airlock_request, user, workspace, user_resource_repo, workspace_service_repo, operation_repo, airlock_request_repo, resource_template_repo, resource_history_repo)
        response.headers["Location"] = construct_location_header(operation)
        return AirlockRequestAndOperationInResponse(airlockRequest=updated_resource, operation=operation)
    except (KeyError, TypeError, EntityDoesNotExist) as e:
        logger.exception("Failed to retrieve Airlock Review configuration for workspace %s", workspace.id)
        raise HTTPException(status_code=status_code.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Failed to retrieve Airlock Review configuration for workspace {workspace.id}.\
                            Please ask your TRE administrator to check the configuration. Details: {str(e)}")
    except (ValidationError, ValueError) as e:
        logger.exception("Failed create user resource model instance due to validation error")
        raise HTTPException(status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Invalid configuration for creating user resource. Please contact your TRE administrator. \
                            Details: {str(e)}")
    except UserNotAuthorizedToUseTemplate as e:
        logger.exception("User not authorized to use template")
        raise HTTPException(status_code=status_code.HTTP_403_FORBIDDEN, detail=str(e))


@airlock_workspace_router.post("/workspaces/{workspace_id}/requests/{airlock_request_id}/review",
                               status_code=status_code.HTTP_200_OK, response_model=AirlockRequestWithAllowedUserActions,
                               name=strings.API_REVIEW_AIRLOCK_REQUEST, dependencies=[Depends(get_current_airlock_manager_user),
                                                                                      Depends(get_workspace_by_id_from_path)])
async def create_airlock_review(
        airlock_review_input: AirlockReviewInCreate,
        airlock_request=Depends(get_airlock_request_by_id_from_path),
        user=Depends(get_current_airlock_manager_user),
        workspace=Depends(get_deployed_workspace_by_id_from_path),
        airlock_request_repo=Depends(get_repository(AirlockRequestRepository)),
        user_resource_repo=Depends(get_repository(UserResourceRepository)),
        workspace_service_repo=Depends(get_repository(WorkspaceServiceRepository)),
        operation_repo=Depends(get_repository(OperationRepository)),
        resource_template_repo=Depends(get_repository(ResourceTemplateRepository)),
        resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> AirlockRequestWithAllowedUserActions:
    try:
        updated_airlock_request = await review_airlock_request(airlock_review_input, airlock_request, user, workspace, airlock_request_repo, user_resource_repo, workspace_service_repo, operation_repo, resource_template_repo, resource_history_repo)
        allowed_actions = get_allowed_actions(updated_airlock_request, user, airlock_request_repo)
        return AirlockRequestWithAllowedUserActions(airlockRequest=updated_airlock_request, allowedUserActions=allowed_actions)
    except (ValidationError, ValueError) as e:
        logger.exception("Failed creating airlock review model instance")
        raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST, detail=str(e))


@airlock_workspace_router.get("/workspaces/{workspace_id}/requests/{airlock_request_id}/link",
                              status_code=status_code.HTTP_200_OK, response_model=AirlockRequestTokenInResponse,
                              name=strings.API_AIRLOCK_REQUEST_LINK,
                              dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager)])
async def get_airlock_container_link_method(workspace=Depends(get_deployed_workspace_by_id_from_path),
                                            airlock_request=Depends(get_airlock_request_by_id_from_path),
                                            user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager)) -> AirlockRequestTokenInResponse:
    container_url = get_airlock_container_link(airlock_request, user, workspace)
    return AirlockRequestTokenInResponse(containerUrl=container_url)
