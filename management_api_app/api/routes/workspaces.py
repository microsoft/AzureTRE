from fastapi import APIRouter, Depends

from api.dependencies.workspaces import get_repository
from db.repositories.workspaces import WorkspaceRepository
from models.schemas.resource import ResourcesInList


router = APIRouter()


@router.get("/workspaces", response_model=ResourcesInList, name="workspaces:get-active-workspaces")
async def retrieve_active_workspaces(
        workspace_repo: WorkspaceRepository = Depends(get_repository(WorkspaceRepository))
) -> ResourcesInList:
    workspaces = workspace_repo.get_all_active_resources()
    return ResourcesInList(resources=workspaces)
