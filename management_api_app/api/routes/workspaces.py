import logging

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from api.dependencies.database import get_repository
from api.dependencies.workspaces import get_workspace_by_workspace_id_from_path
from db.repositories.workspaces import WorkspaceRepository
from models.domain.workspace import Workspace
from models.schemas.workspace import WorkspaceInCreate, WorkspaceIdInResponse, WorkspacesInList, WorkspaceInResponse
from resources import strings
from service_bus.service_bus import ServiceBus


router = APIRouter()


@router.get("/workspaces", response_model=WorkspacesInList, name=strings.API_GET_ALL_WORKSPACES)
async def retrieve_active_workspaces(workspace_repo: WorkspaceRepository = Depends(get_repository(WorkspaceRepository))) -> WorkspacesInList:
    workspaces = workspace_repo.get_all_active_workspaces()
    return WorkspacesInList(workspaces=workspaces)


@router.post("/workspaces", status_code=status.HTTP_202_ACCEPTED, response_model=WorkspaceIdInResponse, name=strings.API_CREATE_WORKSPACE)
async def create_workspace(workspace_create: WorkspaceInCreate, workspace_repo: WorkspaceRepository = Depends(get_repository(WorkspaceRepository))) -> WorkspaceIdInResponse:
    try:
        workspace = workspace_repo.create_workspace_item(workspace_create)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    try:
        workspace_repo.save_workspace(workspace)
    except Exception as e:
        logging.debug(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        service_bus = ServiceBus()
        await service_bus.send_resource_request_message(workspace)
    except Exception as e:
        # TODO: Rollback DB change, issue #154
        logging.debug(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE)

    return WorkspaceIdInResponse(workspaceId=workspace.id)


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceInResponse, name=strings.API_GET_WORKSPACE_BY_ID)
async def retrieve_workspace_by_workspace_id(workspace: Workspace = Depends(get_workspace_by_workspace_id_from_path)) -> WorkspaceInResponse:
    return WorkspaceInResponse(workspace=workspace)
