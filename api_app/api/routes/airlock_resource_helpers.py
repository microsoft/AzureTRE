from datetime import datetime
from collections import defaultdict
import logging
from typing import List

from fastapi import HTTPException
from starlette import status
from db.repositories.airlock_reviews import AirlockReviewRepository
from models.domain.airlock_review import AirlockReview
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.airlock_request import AirlockActions, AirlockRequest, AirlockRequestStatus, AirlockRequestType
from event_grid.event_sender import send_status_changed_event, send_airlock_notification_event
from models.domain.authentication import User
from models.domain.workspace import Workspace
from models.schemas.airlock_request import AirlockRequestWithAllowedUserActions

from resources import strings
from services.authentication import get_access_service


async def save_and_publish_event_airlock_request(airlock_request: AirlockRequest, airlock_request_repo: AirlockRequestRepository, user: User, workspace: Workspace):

    # First check we have some email addresses so we can notify people.
    access_service = get_access_service()
    role_assignment_details = access_service.get_workspace_role_assignment_details(workspace)
    check_email_exists(role_assignment_details)

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
        await send_airlock_notification_event(airlock_request, role_assignment_details["researcher_emails"], role_assignment_details["owner_emails"])
    except Exception as e:
        airlock_request_repo.delete_item(airlock_request.id)
        logging.error(f"Failed sending status_changed message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.EVENT_GRID_GENERAL_ERROR_MESSAGE)


async def update_status_and_publish_event_airlock_request(airlock_request: AirlockRequest, airlock_request_repo: AirlockRequestRepository, user: User, new_status: AirlockRequestStatus, workspace: Workspace, error_message: str = None):
    try:
        logging.debug(f"Updating airlock request item: {airlock_request.id}")
        updated_airlock_request = airlock_request_repo.update_airlock_request_status(airlock_request, new_status, user, error_message)
    except Exception as e:
        logging.error(f'Failed updating airlock_request item {airlock_request}: {e}')
        # If the validation failed, the error was not related to the saving itself
        if e.status_code == 400:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_ILLEGAL_STATUS_CHANGE)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        logging.debug(f"Sending status changed event for airlock request item: {airlock_request.id}")
        await send_status_changed_event(updated_airlock_request)
        access_service = get_access_service()
        role_assignment_details = access_service.get_workspace_role_assignment_details(workspace)
        await send_airlock_notification_event(updated_airlock_request, role_assignment_details["researcher_emails"], role_assignment_details["owner_emails"])
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


def get_timestamp() -> float:
    return datetime.utcnow().timestamp()


def check_email_exists(role_assignment_details: defaultdict(list)):
    if "researcher_emails" not in role_assignment_details or not role_assignment_details["researcher_emails"]:
        logging.error('Creating an airlock request but the researcher does not have an email address.')
        raise HTTPException(status_code=status.HTTP_417_EXPECTATION_FAILED, detail=strings.AIRLOCK_NO_RESEARCHER_EMAIL)
    if "owner_emails" not in role_assignment_details or not role_assignment_details["owner_emails"]:
        logging.error('Creating an airlock request but the workspace owner does not have an email address.')
        raise HTTPException(status_code=status.HTTP_417_EXPECTATION_FAILED, detail=strings.AIRLOCK_NO_OWNER_EMAIL)


def get_airlock_requests_by_user_and_workspace(user: User, workspace: Workspace, airlock_request_repo: AirlockRequestRepository,
                                               creator_user_id: str = None, type: AirlockRequestType = None, status: AirlockRequestStatus = None, awaiting_current_user_review: bool = None) -> List[AirlockRequest]:
    if awaiting_current_user_review:
        if "AirlockManager" not in user.roles:
            return []
        status = AirlockRequestStatus.InReview

    return airlock_request_repo.get_airlock_requests(workspace_id=workspace.id, user_id=creator_user_id, type=type, status=status)


def get_allowed_actions(request: AirlockRequest, user: User, airlock_request_repo: AirlockRequestRepository) -> AirlockRequestWithAllowedUserActions:
    allowed_actions = []

    can_review_request = airlock_request_repo.validate_status_update(request.status, AirlockRequestStatus.ApprovalInProgress)
    can_cancel_request = airlock_request_repo.validate_status_update(request.status, AirlockRequestStatus.Cancelled)
    can_submit_request = airlock_request_repo.validate_status_update(request.status, AirlockRequestStatus.Submitted)

    if can_review_request and "AirlockManager" in user.roles:
        allowed_actions.append(AirlockActions.Review)

    if can_cancel_request and ("WorkspaceOwner" in user.roles or "WorkspaceResearcher" in user.roles):
        allowed_actions.append(AirlockActions.Cancel)

    if can_submit_request and ("WorkspaceOwner" in user.roles or "WorkspaceResearcher" in user.roles):
        allowed_actions.append(AirlockActions.Submit)

    return allowed_actions


def enrich_requests_with_allowed_actions(requests: List[AirlockRequest], user: User, airlock_request_repo: AirlockRequestRepository) -> List[AirlockRequestWithAllowedUserActions]:
    enriched_requests = []
    for request in requests:
        allowed_actions = get_allowed_actions(request, user, airlock_request_repo)
        enriched_requests.append(AirlockRequestWithAllowedUserActions(airlockRequest=request, allowed_user_actions=allowed_actions))
    return enriched_requests
