import logging

from fastapi import APIRouter, Depends, HTTPException, status
from jsonschema.exceptions import ValidationError

from api.dependencies.database import get_repository
from api.dependencies.workspaces import get_workspace_by_workspace_id_from_path, get_deployed_workspace_by_workspace_id_from_path, get_deployed_workspace_service_by_id_from_path, get_workspace_service_by_id_from_path, get_workspace_by_id, get_user_resource_by_id_from_path
from db.repositories.user_resources import UserResourceRepository
from db.repositories.workspaces import WorkspaceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from models.domain.workspace import WorkspaceRole
from models.schemas.user_resource import UserResourceInResponse, UserResourceIdInResponse, UserResourceInCreate, UserResourcesInList
from models.schemas.workspace import WorkspaceInCreate, WorkspaceIdInResponse, WorkspacesInList, WorkspaceInResponse, WorkspacePatchEnabled
from models.schemas.workspace_service import WorkspaceServiceIdInResponse, WorkspaceServiceInCreate, WorkspaceServicesInList, WorkspaceServiceInResponse
from resources import strings
from service_bus.resource_request_sender import send_resource_request_message, RequestAction
from services.authentication import get_current_user, get_current_admin_user, get_access_service

router = APIRouter(dependencies=[Depends(get_current_user)])


async def save_and_deploy_resource(resource, resource_repo):
    try:
        resource_repo.save_item(resource)
    except Exception as e:
        logging.error(f"Failed to save resource in DB: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        await send_resource_request_message(resource, RequestAction.Install)
    except Exception as e:
        resource_repo.delete_item(resource.id)
        logging.error(f"Failed send resource request message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE)


def get_user_role_in_workspace(user, workspace):
    access_service = get_access_service()
    return access_service.get_workspace_role(user, workspace)


def validate_user_is_owner_or_researcher_in_workspace(user, workspace):
    role = get_user_role_in_workspace(user, workspace)
    if (role != WorkspaceRole.Researcher) and (role != WorkspaceRole.Owner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.ACCESS_USER_IS_NOT_OWNER)


@router.get("/workspaces", response_model=WorkspacesInList, name=strings.API_GET_ALL_WORKSPACES)
async def retrieve_users_active_workspaces(user=Depends(get_current_user), workspace_repo=Depends(get_repository(WorkspaceRepository))) -> WorkspacesInList:
    workspaces = workspace_repo.get_active_workspaces()

    access_service = get_access_service()
    user_workspaces = [workspace for workspace in workspaces if access_service.get_workspace_role(user, workspace) != WorkspaceRole.NoRole]

    return WorkspacesInList(workspaces=user_workspaces)


@router.post("/workspaces", status_code=status.HTTP_202_ACCEPTED, response_model=WorkspaceIdInResponse, name=strings.API_CREATE_WORKSPACE, dependencies=[Depends(get_current_admin_user)])
async def create_workspace(workspace_create: WorkspaceInCreate, workspace_repo=Depends(get_repository(WorkspaceRepository))) -> WorkspaceIdInResponse:
    try:
        workspace = workspace_repo.create_workspace_item(workspace_create)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed to create workspace model instance: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await save_and_deploy_resource(workspace, workspace_repo)

    return WorkspaceIdInResponse(workspaceId=workspace.id)


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceInResponse, name=strings.API_GET_WORKSPACE_BY_ID)
async def retrieve_workspace_by_workspace_id(user=Depends(get_current_user), workspace=Depends(get_workspace_by_workspace_id_from_path)) -> WorkspaceInResponse:
    validate_user_is_owner_or_researcher_in_workspace(user, workspace)
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
        previous_deletion_status = workspace_repo.mark_resource_as_deleting(workspace)
    except Exception as e:
        logging.error(f"Failed to delete workspace instance in DB: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        await send_resource_request_message(workspace, RequestAction.UnInstall)
    except Exception as e:
        workspace_repo.restore_previous_deletion_state(workspace, previous_deletion_status)
        logging.error(f"Failed send workspace resource delete message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE)

    return WorkspaceIdInResponse(workspaceId=workspace.id)


@router.get("/workspaces/{workspace_id}/workspace-services", response_model=WorkspaceServicesInList, name=strings.API_GET_ALL_WORKSPACE_SERVICES)
async def retrieve_users_active_workspace_services(user=Depends(get_current_user), workspace=Depends(get_workspace_by_workspace_id_from_path), workspace_services_repo=Depends(get_repository(WorkspaceServiceRepository))) -> WorkspaceServicesInList:
    validate_user_is_owner_or_researcher_in_workspace(user, workspace)
    workspace_services = workspace_services_repo.get_active_workspace_services_for_workspace(workspace.id)
    return WorkspaceServicesInList(workspaceServices=workspace_services)


@router.post("/workspaces/{workspace_id}/workspace-services", status_code=status.HTTP_202_ACCEPTED, response_model=WorkspaceServiceIdInResponse, name=strings.API_CREATE_WORKSPACE_SERVICE)
async def create_workspace_service(workspace_service_input: WorkspaceServiceInCreate, workspace_service_repo=Depends(get_repository(WorkspaceServiceRepository)), user=Depends(get_current_user), workspace=Depends(get_workspace_by_workspace_id_from_path)) -> WorkspaceServiceIdInResponse:
    validate_user_is_owner_or_researcher_in_workspace(user, workspace)

    try:
        workspace_service = workspace_service_repo.create_workspace_service_item(workspace_service_input, workspace.id)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed create workspace service model instance: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await save_and_deploy_resource(workspace_service, workspace_service_repo)

    return WorkspaceServiceIdInResponse(workspaceServiceId=workspace_service.id)


@router.post("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources", status_code=status.HTTP_202_ACCEPTED, response_model=UserResourceIdInResponse, name=strings.API_CREATE_USER_RESOURCE)
async def create_user_resource(user_resource_create: UserResourceInCreate, user_resource_repo=Depends(get_repository(UserResourceRepository)), user=Depends(get_current_user), workspace=Depends(get_deployed_workspace_by_workspace_id_from_path), workspace_service=Depends(get_deployed_workspace_service_by_id_from_path)) -> UserResourceIdInResponse:
    validate_user_is_owner_or_researcher_in_workspace(user, workspace)

    try:
        user_resource = user_resource_repo.create_user_resource_item(user_resource_create, workspace.id, workspace_service.id, user.id)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed create user resource model instance: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await save_and_deploy_resource(user_resource, user_resource_repo)

    return UserResourceIdInResponse(resourceId=user_resource.id)


@router.get("/workspace-services/{service_id}", response_model=WorkspaceServiceInResponse, name=strings.API_GET_WORKSPACE_SERVICE_BY_ID)
async def retrieve_workspace_service_by_id(workspace_service=Depends(get_workspace_service_by_id_from_path), workspaces_repo=Depends(get_repository(WorkspaceRepository)), user=Depends(get_current_user)) -> WorkspaceServiceInResponse:
    workspace = get_workspace_by_id(workspace_service.workspaceId, workspaces_repo)
    validate_user_is_owner_or_researcher_in_workspace(user, workspace)
    return WorkspaceServiceInResponse(workspaceService=workspace_service)


@router.get("/workspace-services/{service_id}/user-resources", response_model=UserResourcesInList, name=strings.API_GET_MY_USER_RESOURCES)
async def retrieve_user_resources_for_workspace_service(service_id: str, user=Depends(get_current_user), user_resource_repo=Depends(get_repository(UserResourceRepository)), workspace_repo=Depends(get_repository(WorkspaceRepository))) -> UserResourcesInList:
    user_resources = user_resource_repo.get_user_resources_for_workspace_service(service_id)
    if len(user_resources) > 0:
        workspace = get_workspace_by_id(user_resources[0].workspaceId, workspace_repo)
        role = get_user_role_in_workspace(user, workspace)
        if role != WorkspaceRole.Researcher and role != WorkspaceRole.Owner:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.ACCESS_USER_IS_NOT_OWNER_OR_RESEARCHER)
        if role == WorkspaceRole.Researcher:
            # filter only to the user - for researchers
            user_resources = [resource for resource in user_resources if resource.ownerId == user.id]
    return UserResourcesInList(userResources=user_resources)


@router.get("/user-resources/{resource_id}", response_model=UserResourceInResponse, name=strings.API_GET_USER_RESOURCE)
async def retrieve_user_resource_by_id(user_resource=Depends(get_user_resource_by_id_from_path), user=Depends(get_current_user), workspace_repo=Depends(get_repository(WorkspaceRepository))) -> UserResourceInResponse:
    workspace = get_workspace_by_id(user_resource.workspaceId, workspace_repo)
    role = get_user_role_in_workspace(user, workspace)
    if role == WorkspaceRole.Owner or (role == WorkspaceRole.Researcher and user_resource.ownerId == user.id):
        return UserResourceInResponse(userResource=user_resource)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.ACCESS_USER_IS_NOT_OWNER_OR_RESEARCHER)
