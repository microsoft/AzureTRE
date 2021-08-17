from fastapi import Depends, HTTPException, Path
from pydantic import UUID4
from starlette import status

from api.dependencies.database import get_repository
from db.errors import ResourceIsNotDeployed
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.errors import EntityDoesNotExist
from db.repositories.workspaces import WorkspaceRepository
from models.domain.workspace import Workspace
from models.domain.workspace_service import WorkspaceService
from resources import strings


async def get_workspace_by_workspace_id_from_path(workspace_id: UUID4 = Path(...), workspaces_repo=Depends(get_repository(WorkspaceRepository))) -> Workspace:
    try:
        return workspaces_repo.get_workspace_by_workspace_id(workspace_id)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_DOES_NOT_EXIST)


async def get_deployed_workspace_by_workspace_id_from_path(workspace_id: UUID4 = Path(...), workspaces_repo=Depends(get_repository(WorkspaceRepository))) -> Workspace:
    try:
        return workspaces_repo.get_deployed_workspace_by_workspace_id(workspace_id)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_DOES_NOT_EXIST)
    except ResourceIsNotDeployed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_IS_NOT_DEPLOYED)


async def get_deployed_workspace_service_by_id_from_path(service_id: UUID4 = Path(...), workspace_services_repo=Depends(get_repository(WorkspaceServiceRepository))) -> WorkspaceService:
    try:
        return workspace_services_repo.get_deployed_workspace_service_by_id(service_id)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_SERVICE_DOES_NOT_EXIST)
    except ResourceIsNotDeployed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_SERVICE_IS_NOT_DEPLOYED)
