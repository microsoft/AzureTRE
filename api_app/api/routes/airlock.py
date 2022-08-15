import logging

from fastapi import APIRouter, Depends, HTTPException, status

from jsonschema.exceptions import ValidationError

from api.dependencies.database import get_repository
from api.dependencies.workspaces import get_workspace_by_id_from_path, get_deployed_workspace_by_id_from_path
from api.dependencies.airlock import get_airlock_request_by_id_from_path
from models.domain.airlock_request import AirlockRequestStatus, AirlockRequestType
from db.repositories.airlock_reviews import AirlockReviewRepository
from models.schemas.airlock_request_url import AirlockRequestTokenInResponse
from models.schemas.airlock_review import AirlockReviewInCreate, AirlockReviewInResponse

from db.repositories.airlock_requests import AirlockRequestRepository
from models.schemas.airlock_request import AirlockRequestInCreate, AirlockRequestInResponse, AirlockRequestWithAllowedUserActionsInList
from resources import strings
from services.authentication import get_current_workspace_owner_or_researcher_user_or_airlock_manager, get_current_workspace_owner_or_researcher_user, get_current_airlock_manager_user

from .airlock_resource_helpers import save_airlock_review, save_and_publish_event_airlock_request, \
    update_status_and_publish_event_airlock_request, enrich_requests_with_allowed_actions, get_airlock_requests_by_user_and_workspace

from services.airlock import validate_user_allowed_to_access_storage_account, \
    get_account_by_request, get_airlock_request_container_sas_token, validate_request_status

airlock_workspace_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager)])


# airlock
@airlock_workspace_router.post("/workspaces/{workspace_id}/requests", status_code=status.HTTP_201_CREATED, response_model=AirlockRequestInResponse, name=strings.API_CREATE_AIRLOCK_REQUEST, dependencies=[Depends(get_current_workspace_owner_or_researcher_user), Depends(get_workspace_by_id_from_path)])
async def create_draft_request(airlock_request_input: AirlockRequestInCreate, user=Depends(get_current_workspace_owner_or_researcher_user), airlock_request_repo=Depends(get_repository(AirlockRequestRepository)), workspace=Depends(get_deployed_workspace_by_id_from_path)) -> AirlockRequestInResponse:
    if workspace.properties.get("enable_airlock") is False:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail=strings.AIRLOCK_NOT_ENABLED_IN_WORKSPACE)
    try:
        airlock_request = airlock_request_repo.create_airlock_request_item(airlock_request_input, workspace.id)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed creating airlock request model instance: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    await save_and_publish_event_airlock_request(airlock_request, airlock_request_repo, user, workspace)
    return AirlockRequestInResponse(airlockRequest=airlock_request)


@airlock_workspace_router.get("/workspaces/{workspace_id}/requests",
                              status_code=status.HTTP_200_OK,
                              response_model=AirlockRequestWithAllowedUserActionsInList,
                              name=strings.API_LIST_AIRLOCK_REQUESTS,
                              dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager), Depends(get_workspace_by_id_from_path)])
async def get_all_airlock_requests_by_workspace(
        airlock_request_repo=Depends(get_repository(AirlockRequestRepository)),
        workspace=Depends(get_deployed_workspace_by_id_from_path),
        user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager),
        creator_user_id: str = None, type: AirlockRequestType = None, status: AirlockRequestStatus = None, awaiting_current_user_review: bool = None) -> AirlockRequestWithAllowedUserActionsInList:
    try:
        airlock_requests = get_airlock_requests_by_user_and_workspace(user=user, workspace=workspace, airlock_request_repo=airlock_request_repo,
                                                                      creator_user_id=creator_user_id, type=type, status=status, awaiting_current_user_review=awaiting_current_user_review)
        airlock_requests_with_allowed_user_actions = enrich_requests_with_allowed_actions(airlock_requests, user, airlock_request_repo)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed retrieving all the airlock requests for a workspace: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return AirlockRequestWithAllowedUserActionsInList(airlockRequests=airlock_requests_with_allowed_user_actions)


@airlock_workspace_router.get("/workspaces/{workspace_id}/requests/{airlock_request_id}", status_code=status.HTTP_200_OK, response_model=AirlockRequestInResponse, name=strings.API_GET_AIRLOCK_REQUEST, dependencies=[Depends(get_current_workspace_owner_or_researcher_user), Depends(get_workspace_by_id_from_path)])
async def retrieve_airlock_request_by_id(airlock_request=Depends(get_airlock_request_by_id_from_path)) -> AirlockRequestInResponse:
    return AirlockRequestInResponse(airlockRequest=airlock_request)


@airlock_workspace_router.post("/workspaces/{workspace_id}/requests/{airlock_request_id}/submit", status_code=status.HTTP_200_OK, response_model=AirlockRequestInResponse, name=strings.API_SUBMIT_AIRLOCK_REQUEST, dependencies=[Depends(get_current_workspace_owner_or_researcher_user), Depends(get_workspace_by_id_from_path)])
async def create_submit_request(airlock_request=Depends(get_airlock_request_by_id_from_path), user=Depends(get_current_workspace_owner_or_researcher_user), airlock_request_repo=Depends(get_repository(AirlockRequestRepository)), workspace=Depends(get_workspace_by_id_from_path)) -> AirlockRequestInResponse:
    updated_resource = await update_status_and_publish_event_airlock_request(airlock_request, airlock_request_repo, user, AirlockRequestStatus.Submitted, workspace)
    return AirlockRequestInResponse(airlockRequest=updated_resource)


@airlock_workspace_router.post("/workspaces/{workspace_id}/requests/{airlock_request_id}/cancel", status_code=status.HTTP_200_OK, response_model=AirlockRequestInResponse, name=strings.API_CANCEL_AIRLOCK_REQUEST, dependencies=[Depends(get_current_workspace_owner_or_researcher_user), Depends(get_workspace_by_id_from_path)])
async def create_cancel_request(airlock_request=Depends(get_airlock_request_by_id_from_path), user=Depends(get_current_workspace_owner_or_researcher_user), airlock_request_repo=Depends(get_repository(AirlockRequestRepository)), workspace=Depends(get_workspace_by_id_from_path)) -> AirlockRequestInResponse:
    updated_resource = await update_status_and_publish_event_airlock_request(airlock_request, airlock_request_repo, user, AirlockRequestStatus.Cancelled, workspace)
    return AirlockRequestInResponse(airlockRequest=updated_resource)


@airlock_workspace_router.post("/workspaces/{workspace_id}/requests/{airlock_request_id}/reviews", status_code=status.HTTP_200_OK, response_model=AirlockReviewInResponse, name=strings.API_REVIEW_AIRLOCK_REQUEST, dependencies=[Depends(get_current_airlock_manager_user), Depends(get_workspace_by_id_from_path)])
async def create_airlock_review(airlock_review_input: AirlockReviewInCreate, airlock_request=Depends(get_airlock_request_by_id_from_path), user=Depends(get_current_airlock_manager_user), airlock_request_repo=Depends(get_repository(AirlockRequestRepository)), airlock_review_repo=Depends(get_repository(AirlockReviewRepository)), workspace=Depends(get_deployed_workspace_by_id_from_path)) -> AirlockReviewInResponse:
    # Create the review model and save in cosmos
    try:
        airlock_review = airlock_review_repo.create_airlock_review_item(airlock_review_input, workspace.id, airlock_request.id)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed creating airlock review model instance: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # Update the airlock request in cosmos, send a status_changed event
    await save_airlock_review(airlock_review, airlock_review_repo, user)
    review_status = AirlockRequestStatus(airlock_review.reviewDecision.value)
    await update_status_and_publish_event_airlock_request(airlock_request, airlock_request_repo, user, review_status, workspace)
    return AirlockReviewInResponse(airlock_review=airlock_review)


@airlock_workspace_router.get("/workspaces/{workspace_id}/requests/{airlock_request_id}/link",
                              status_code=status.HTTP_200_OK, response_model=AirlockRequestTokenInResponse,
                              name=strings.API_AIRLOCK_REQUEST_LINK,
                              dependencies=[Depends(get_current_workspace_owner_or_researcher_user)])
async def get_airlock_container_link(workspace=Depends(get_deployed_workspace_by_id_from_path),
                                     airlock_request=Depends(get_airlock_request_by_id_from_path),
                                     user=Depends(get_current_workspace_owner_or_researcher_user)) -> AirlockRequestTokenInResponse:
    validate_user_allowed_to_access_storage_account(user, airlock_request)
    validate_request_status(airlock_request)
    account_name: str = get_account_by_request(airlock_request, workspace)
    container_url = get_airlock_request_container_sas_token(account_name, airlock_request)
    return AirlockRequestTokenInResponse(containerUrl=container_url)
