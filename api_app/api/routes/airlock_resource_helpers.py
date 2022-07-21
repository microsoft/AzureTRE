from datetime import datetime
import logging

from fastapi import HTTPException
from starlette import status
from db.repositories.airlock_reviews import AirlockReviewRepository
from models.domain.airlock_review import AirlockReview
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus
from event_grid.event_sender import send_status_changed_event, send_airlock_notification_event
from models.domain.authentication import User
from models.domain.workspace import Workspace

from resources import strings
from services.authentication import get_access_service


class RequestAccountDetails:
    account_name: str
    account_rg: str

    def __init__(self, account_name, account_rg):
        self.account_name = account_name
        self.account_rg = account_rg


async def save_and_publish_event_airlock_request(airlock_request: AirlockRequest, airlock_request_repo: AirlockRequestRepository, user: User, workspace: Workspace):
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
        access_service = get_access_service()
        role_assignment_details = access_service.get_workspace_role_assignment_details(workspace)
        await send_airlock_notification_event(airlock_request, role_assignment_details["researcher_emails"], role_assignment_details["owner_emails"])
    except Exception as e:
        airlock_request_repo.delete_item(airlock_request.id)
        logging.error(f"Failed sending status_changed message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.EVENT_GRID_GENERAL_ERROR_MESSAGE)


async def update_status_and_publish_event_airlock_request(airlock_request: AirlockRequest, airlock_request_repo: AirlockRequestRepository, user: User, new_status: AirlockRequestStatus, workspace: Workspace):
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
