from fastapi import Depends, HTTPException, Path, status
from pydantic import UUID4

from api.dependencies.database import get_repository
from db.errors import EntityDoesNotExist
from resources import strings
from models.domain.shared_service import SharedService


def get_shared_service_by_id(shared_service_id: UUID4, shared_services_repo) -> SharedService:
    try:
        return shared_services_repo.get_shared_service_by_id(shared_service_id)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.SHARED_SERVICE_DOES_NOT_EXIST)


async def get_shared_service_by_id_from_path(shared_service_id: UUID4 = Path(...), shared_service_repo=Depends(get_repository(WorkspaceRepository))) -> Workspace:
    return get_shared_service_by_id(shared_service_id, shared_service_repo)
