from fastapi import APIRouter, Depends
from starlette import status

from api.dependencies.workspaces import get_repository, get_workspace_by_workspace_id_from_path
from db.repositories.workspaces import WorkspaceRepository
from models.domain.resource import Resource
from models.schemas.resource import ResourcesInList, ResourceInResponse, WorkspaceInCreate
from resources import strings


router = APIRouter()


@router.get("/workspaces", response_model=ResourcesInList, name=strings.API_GET_ALL_WORKSPACES)
async def retrieve_active_workspaces(workspace_repo: WorkspaceRepository = Depends(get_repository(WorkspaceRepository))) -> ResourcesInList:
    workspaces = workspace_repo.get_all_active_workspaces()
    return ResourcesInList(resources=workspaces)


@router.post("/workspaces", status_code=status.HTTP_202_ACCEPTED, response_model=ResourceInResponse, name=strings.API_CREATE_WORKSPACE)
async def create_workspace(workspace_create: WorkspaceInCreate, workspace_repo: WorkspaceRepository = Depends(get_repository(WorkspaceRepository))) -> ResourceInResponse:
    workspace = workspace_repo.create_workspace(workspace_create)
    return ResourceInResponse(resource=workspace)


@router.get("/workspaces/{workspace_id}", response_model=ResourceInResponse, name=strings.API_GET_WORKSPACE_BY_ID)
async def retrieve_workspace_by_workspace_id(workspace: Resource = Depends(get_workspace_by_workspace_id_from_path)) -> ResourceInResponse:
    return ResourceInResponse(resource=workspace)
