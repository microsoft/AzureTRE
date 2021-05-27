from fastapi import APIRouter, Depends

from api.dependencies.workspaces import get_repository, get_workspace_by_workspace_id_from_path
from db.repositories.workspaces import WorkspaceRepository
from models.domain.resource import Resource
from models.schemas.resource import ResourcesInList, ResourceInResponse


router = APIRouter()


@router.get("/workspaces", response_model=ResourcesInList, name="workspaces:get-active-workspaces")
async def retrieve_active_workspaces(
        workspace_repo: WorkspaceRepository = Depends(get_repository(WorkspaceRepository))
) -> ResourcesInList:
    workspaces = workspace_repo.get_all_active_workspaces()
    return ResourcesInList(resources=workspaces)


@router.get("/workspaces/{workspace_id}", response_model=ResourceInResponse, name="workspaces:get-workspace")
async def retrieve_workspace_by_workspace_id(
        workspace: Resource = Depends(get_workspace_by_workspace_id_from_path)
) -> ResourceInResponse:
    return ResourceInResponse(resource=workspace)
