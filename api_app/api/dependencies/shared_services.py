from fastapi import Depends, HTTPException, Path, status
from pydantic import UUID4

from api.helpers import get_repository
from db.errors import EntityDoesNotExist
from resources import strings
from models.domain.shared_service import SharedService
from models.domain.operation import Operation
from db.repositories.shared_services import SharedServiceRepository
from db.repositories.operations import OperationRepository


async def get_shared_service_by_id(shared_service_id: UUID4, shared_services_repo) -> SharedService:
    try:
        return await shared_services_repo.get_shared_service_by_id(shared_service_id)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.SHARED_SERVICE_DOES_NOT_EXIST)


async def get_shared_service_by_id_from_path(shared_service_id: UUID4 = Path(...), shared_service_repo=Depends(get_repository(SharedServiceRepository))) -> SharedService:
    return await get_shared_service_by_id(shared_service_id, shared_service_repo)


async def get_operation_by_id_from_path(operation_id: UUID4 = Path(...), operations_repo=Depends(get_repository(OperationRepository))) -> Operation:
    try:
        return await operations_repo.get_operation_by_id(operation_id=operation_id)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.OPERATION_DOES_NOT_EXIST)
