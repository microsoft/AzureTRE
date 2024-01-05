from fastapi import Depends, HTTPException, Path, status
from pydantic import UUID4

from api.helpers import get_repository
from db.errors import EntityDoesNotExist, ResourceIsNotDeployed
from db.repositories.operations import OperationRepository
from db.repositories.user_resources import UserResourceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.workspaces import WorkspaceRepository
from models.domain.user_resource import UserResource
from models.domain.workspace import Workspace
from models.domain.workspace_service import WorkspaceService
from models.domain.operation import Operation

from resources import strings


async def get_workspace_by_id(workspace_id: UUID4, workspaces_repo) -> Workspace:
    try:
        return await workspaces_repo.get_workspace_by_id(workspace_id)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_DOES_NOT_EXIST)


async def get_workspace_by_id_from_path(workspace_id: UUID4 = Path(...), workspaces_repo=Depends(get_repository(WorkspaceRepository))) -> Workspace:
    return await get_workspace_by_id(workspace_id, workspaces_repo)


async def get_deployed_workspace_by_id_from_path(workspace_id: UUID4 = Path(...), workspaces_repo=Depends(get_repository(WorkspaceRepository)), operations_repo=Depends(get_repository(OperationRepository))) -> Workspace:
    try:
        return await workspaces_repo.get_deployed_workspace_by_id(workspace_id, operations_repo)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_DOES_NOT_EXIST)
    except ResourceIsNotDeployed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_IS_NOT_DEPLOYED)


async def get_workspace_service_by_id_from_path(workspace_id: UUID4 = Path(...), service_id: UUID4 = Path(...), workspace_services_repo=Depends(get_repository(WorkspaceServiceRepository))) -> WorkspaceService:
    try:
        return await workspace_services_repo.get_workspace_service_by_id(workspace_id, service_id)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_SERVICE_DOES_NOT_EXIST)


async def get_deployed_workspace_service_by_id_from_path(workspace_id: UUID4 = Path(...), service_id: UUID4 = Path(...), workspace_services_repo=Depends(get_repository(WorkspaceServiceRepository)), operations_repo=Depends(get_repository(OperationRepository))) -> WorkspaceService:
    try:
        return await workspace_services_repo.get_deployed_workspace_service_by_id(workspace_id, service_id, operations_repo)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_SERVICE_DOES_NOT_EXIST)
    except ResourceIsNotDeployed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_SERVICE_IS_NOT_DEPLOYED)


async def get_user_resource_by_id_from_path(workspace_id: UUID4 = Path(...), service_id: UUID4 = Path(...), resource_id: UUID4 = Path(...), user_resource_repo=Depends(get_repository(UserResourceRepository))) -> UserResource:
    try:
        return await user_resource_repo.get_user_resource_by_id(workspace_id, service_id, resource_id)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.USER_RESOURCE_DOES_NOT_EXIST)


async def get_operation_by_id_from_path(operation_id: UUID4 = Path(...), operations_repo=Depends(get_repository(OperationRepository))) -> Operation:
    try:
        return await operations_repo.get_operation_by_id(operation_id=operation_id)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.OPERATION_DOES_NOT_EXIST)
