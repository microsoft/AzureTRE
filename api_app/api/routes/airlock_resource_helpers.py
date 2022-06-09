from datetime import datetime
import logging

from fastapi import HTTPException
from starlette import status
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus
from event_grid.helpers import send_status_changed_event
from models.domain.authentication import User

from resources import strings


async def save_and_publish_event_airlock_request(resource: AirlockRequest, resource_repo: AirlockRequestRepository, user: User):
    try:
        resource.user = user
        resource.updatedWhen = get_timestamp()
        resource_repo.save_item(resource)
    except Exception as e:
        logging.error(f'Failed saving resource item {resource}: {e}')
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        await send_status_changed_event(resource)
    except Exception as e:
        resource_repo.delete_item(resource.id)
        logging.error(f"Failed send resource request message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.EVENT_GRID_GENERAL_ERROR_MESSAGE)


async def update_status_and_publish_event_airlock_request(resource: AirlockRequest, resource_repo: AirlockRequestRepository, user: User, status: AirlockRequestStatus):
    try:
        updated_resource = resource_repo.update_airlock_request_status(resource, status, user)
    except Exception as e:
        logging.error(f'Failed updating resource item {resource}: {e}')
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        await send_status_changed_event(resource)
        return updated_resource
    except Exception as e:
        logging.error(f"Failed send resource request message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.EVENT_GRID_GENERAL_ERROR_MESSAGE)


def get_timestamp() -> float:
    return datetime.utcnow().timestamp()
