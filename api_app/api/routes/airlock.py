import logging

from fastapi import APIRouter, Depends, HTTPException, status

from jsonschema.exceptions import ValidationError

from api.dependencies.database import get_repository
from api.dependencies.workspaces import get_workspace_by_id_from_path, get_deployed_workspace_by_id_from_path
from api.dependencies.airlock import get_airlock_request_by_id_from_path
from models.domain.airlock_request import AirlockRequestStatus
from db.repositories.airlock_reviews import AirlockReviewRepository
from models.schemas.airlock_review import AirlockReviewInCreate, AirlockReviewInResponse

from db.repositories.airlock_requests import AirlockRequestRepository
from models.schemas.airlock_request import AirlockRequestInCreate, AirlockRequestInResponse
from resources import strings
from services.authentication import get_current_workspace_owner_or_researcher_user, get_current_workspace_owner_user

from .airlock_resource_helpers import save_airlock_review, save_and_publish_event_airlock_request, update_status_and_publish_event_airlock_request

airlock_workspace_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_researcher_user)])


# airlock
@airlock_workspace_router.post("/workspaces/{workspace_id}/requests", status_code=status.HTTP_201_CREATED, response_model=AirlockRequestInResponse, name=strings.API_CREATE_AIRLOCK_REQUEST, dependencies=[Depends(get_workspace_by_id_from_path)])
async def create_draft_request(airlock_request_input: AirlockRequestInCreate, user=Depends(get_current_workspace_owner_or_researcher_user), airlock_request_repo=Depends(get_repository(AirlockRequestRepository)), workspace=Depends(get_deployed_workspace_by_id_from_path)) -> AirlockRequestInResponse:
    try:
        airlock_request = airlock_request_repo.create_airlock_request_item(airlock_request_input, workspace.id)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed creating airlock request model instance: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    await save_and_publish_event_airlock_request(airlock_request, airlock_request_repo, user)
    return AirlockRequestInResponse(airlock_request=airlock_request)


@airlock_workspace_router.post("/workspaces/{workspace_id}/requests/{airlock_request_id}/submit", status_code=status.HTTP_200_OK, response_model=AirlockRequestInResponse, name=strings.API_SUBMIT_AIRLOCK_REQUEST, dependencies=[Depends(get_workspace_by_id_from_path)])
async def create_submit_request(airlock_request=Depends(get_airlock_request_by_id_from_path), user=Depends(get_current_workspace_owner_or_researcher_user), airlock_request_repo=Depends(get_repository(AirlockRequestRepository))) -> AirlockRequestInResponse:
    updated_resource = await update_status_and_publish_event_airlock_request(airlock_request, airlock_request_repo, user, AirlockRequestStatus.Submitted)
    return AirlockRequestInResponse(airlock_request=updated_resource)


@airlock_workspace_router.post("/workspaces/{workspace_id}/requests/{airlock_request_id}/reviews", status_code=status.HTTP_200_OK, response_model=AirlockReviewInResponse, name=strings.API_REVIEW_AIRLOCK_REQUEST, dependencies=[Depends(get_workspace_by_id_from_path)])
async def create_airlock_review(airlock_review_input: AirlockReviewInCreate, airlock_request=Depends(get_airlock_request_by_id_from_path), user=Depends(get_current_workspace_owner_user), airlock_request_repo=Depends(get_repository(AirlockRequestRepository)), airlock_review_repo=Depends(get_repository(AirlockReviewRepository)), workspace=Depends(get_deployed_workspace_by_id_from_path)) -> AirlockReviewInResponse:
    # Create the review model and save in cosmos
    try:
        airlock_review = airlock_review_repo.create_airlock_review_item(airlock_review_input, workspace.id, airlock_request.id)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed creating airlock review model instance: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # Update the airlock request in cosmos, send a status_changed event
    await save_airlock_review(airlock_review, airlock_review_repo, user)
    await update_status_and_publish_event_airlock_request(airlock_request, airlock_request_repo, user, airlock_review.reviewDecision)
    return AirlockReviewInResponse(airlock_review=airlock_review)
