import logging

from fastapi import APIRouter, Depends, HTTPException
from jsonschema.exceptions import ValidationError
from starlette import status

from api.dependencies.database import get_repository
from api.dependencies.workspaces import get_workspace_by_workspace_id_from_path
from db.repositories.workspaces import WorkspaceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from models.domain.workspace import WorkspaceRole
from models.schemas.workspace import WorkspaceInCreate, WorkspaceIdInResponse, WorkspacesInList, WorkspaceInResponse, WorkspacePatchEnabled
from models.schemas.workspace_service import WorkspaceServiceIdInResponse, WorkspaceServiceInCreate
from resources import strings
from service_bus.resource_request_sender import send_resource_request_message, RequestAction
from services.authentication import get_current_user, get_current_admin_user, get_access_service


router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/workspaces", response_model=WorkspacesInList, name=strings.API_GET_ALL_WORKSPACES)
async def retrieve_users_active_workspaces(user=Depends(get_current_user), workspace_repo=Depends(get_repository(WorkspaceRepository))) -> WorkspacesInList:
    workspaces = workspace_repo.get_all_active_workspaces()

    access_service = get_access_service()
    user_workspaces = [workspace for workspace in workspaces if access_service.get_workspace_role(user, workspace) != WorkspaceRole.NoRole]

    return WorkspacesInList(workspaces=user_workspaces)


@router.post("/workspaces", status_code=status.HTTP_202_ACCEPTED, response_model=WorkspaceIdInResponse, name=strings.API_CREATE_WORKSPACE, dependencies=[Depends(get_current_admin_user)])
async def create_workspace(workspace_create: WorkspaceInCreate, workspace_repo: WorkspaceRepository = Depends(get_repository(WorkspaceRepository))) -> WorkspaceIdInResponse:
    try:
        workspace = workspace_repo.create_workspace_item(workspace_create)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed to create workspace model instance: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    try:
        workspace_repo.save_workspace(workspace)
    except Exception as e:
        logging.error(f"Failed to save workspace instance in DB: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        await send_resource_request_message(workspace, RequestAction.Install)
    except Exception as e:
        workspace_repo.delete_resource(workspace.id)
        logging.error(f"Failed send workspace resource request message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE)

    return WorkspaceIdInResponse(workspaceId=workspace.id)


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceInResponse, name=strings.API_GET_WORKSPACE_BY_ID)
async def retrieve_workspace_by_workspace_id(user=Depends(get_current_user), workspace=Depends(get_workspace_by_workspace_id_from_path)) -> WorkspaceInResponse:
    access_service = get_access_service()
    if access_service.get_workspace_role(user, workspace) == WorkspaceRole.NoRole:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.ACCESS_USER_IS_NOT_OWNER_OR_RESEARCHER)

    return WorkspaceInResponse(workspace=workspace)


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceInResponse, name=strings.API_UPDATE_WORKSPACE, dependencies=[Depends(get_current_admin_user)])
async def patch_workspace(workspace_patch: WorkspacePatchEnabled, workspace=Depends(get_workspace_by_workspace_id_from_path), workspace_repo=Depends(get_repository(WorkspaceRepository))) -> WorkspaceInResponse:
    workspace_repo.patch_workspace(workspace, workspace_patch)
    return WorkspaceInResponse(workspace=workspace)


@router.delete("/workspaces/{workspace_id}", response_model=WorkspaceIdInResponse, name=strings.API_DELETE_WORKSPACE, dependencies=[Depends(get_current_admin_user)])
async def delete_workspace(workspace=Depends(get_workspace_by_workspace_id_from_path), workspace_repo=Depends(get_repository(WorkspaceRepository)), workspace_service_repo=Depends(get_repository(WorkspaceServiceRepository))) -> WorkspaceIdInResponse:
    if workspace.is_enabled():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.WORKSPACE_NEEDS_TO_BE_DISABLED_BEFORE_DELETION)
    if len(workspace_service_repo.get_active_workspace_services_for_workspace(workspace.id)) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.WORKSPACE_SERVICES_NEED_TO_BE_DELETED_BEFORE_WORKSPACE)

    try:
        workspace_repo.mark_workspace_as_deleted(workspace)
    except Exception as e:
        logging.error(f"Failed to delete workspace instance in DB: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        await send_resource_request_message(workspace, RequestAction.UnInstall)
    except Exception as e:
        workspace_repo.mark_workspace_as_not_deleted(workspace)
        logging.error(f"Failed send workspace resource delete message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE)

    return WorkspaceIdInResponse(workspaceId=workspace.id)


@router.post("/workspaces/{workspace_id}/workspace-services", status_code=status.HTTP_202_ACCEPTED, response_model=WorkspaceServiceIdInResponse, name=strings.API_CREATE_WORKSPACE_SERVICE)
async def create_workspace_service(workspace_input: WorkspaceServiceInCreate, workspace_service_repo=Depends(get_repository(WorkspaceServiceRepository)), user=Depends(get_current_user), workspace=Depends(get_workspace_by_workspace_id_from_path)) -> WorkspaceServiceIdInResponse:
    access_service = get_access_service()
    if access_service.get_workspace_role(user, workspace) != WorkspaceRole.Owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.ACCESS_USER_IS_NOT_OWNER)

    try:
        workspace_service = workspace_service_repo.create_workspace_service_item(workspace_input, workspace.id)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed create workspace service model instance: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    try:
        workspace_service_repo.save_workspace_service(workspace_service)
    except Exception as e:
        logging.error(f"Failed save workspace service instance in DB: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        await send_resource_request_message(workspace_service, RequestAction.Install)
    except Exception as e:
        workspace_service_repo.delete_resource(workspace_service.id)
        logging.error(f"Failed send workspace service resource request message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE)

    return WorkspaceServiceIdInResponse(workspaceServiceId=workspace_service.id)
