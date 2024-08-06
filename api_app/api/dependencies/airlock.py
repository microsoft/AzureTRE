from fastapi import Depends, HTTPException, Path, status
from pydantic import UUID4

from api.helpers import get_repository
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.airlock_request import AirlockRequest
from db.errors import EntityDoesNotExist, UnableToAccessDatabase
from resources import strings


async def get_airlock_request_by_id(airlock_request_id: UUID4, airlock_request_repo: AirlockRequestRepository) -> AirlockRequest:
    try:
        return await airlock_request_repo.get_airlock_request_by_id(airlock_request_id)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.AIRLOCK_REQUEST_DOES_NOT_EXIST)
    except UnableToAccessDatabase:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)


async def get_airlock_request_by_id_from_path(airlock_request_id: UUID4 = Path(...), airlock_request_repo=Depends(get_repository(AirlockRequestRepository))) -> AirlockRequest:
    return await get_airlock_request_by_id(airlock_request_id, airlock_request_repo)
