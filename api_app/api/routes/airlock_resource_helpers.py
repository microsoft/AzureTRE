from datetime import datetime
import logging

from fastapi import HTTPException
from starlette import status
from models.domain.airlock_resource import AirlockRequestStatus
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.airlock_request import AirlockRequest
from event_grid.helpers import send_status_changed_event
from models.domain.authentication import User

from resources import strings


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
        logging.error(f"Failed send airlock_request request message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.EVENT_GRID_GENERAL_ERROR_MESSAGE)


async def update_status_and_publish_event_airlock_request(airlock_request: AirlockRequest, airlock_request_repo: AirlockRequestRepository, user: User, status: AirlockRequestStatus):
    try:
        logging.debug(f"Saving airlock request item: {airlock_request.id}")
        updated_airlock_request = airlock_request_repo.update_airlock_request_status(airlock_request, status, user)
    except Exception as e:
        logging.error(f'Failed updating airlock_request item {airlock_request}: {e}')
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        logging.debug(f"Sending status changed event for airlock request item: {airlock_request.id}")
        await send_status_changed_event(airlock_request)
        return updated_airlock_request
    except Exception as e:
        logging.error(f"Failed send airlock_request request message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.EVENT_GRID_GENERAL_ERROR_MESSAGE)


def get_timestamp() -> float:
    return datetime.utcnow().timestamp()
