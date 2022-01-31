import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request, Path

from jsonschema.exceptions import ValidationError
from pydantic.types import UUID4

from api.dependencies.database import get_repository
from api.dependencies.workspaces import get_operation_by_id_from_path, get_workspace_by_id_from_path, get_deployed_workspace_by_id_from_path, get_deployed_workspace_service_by_id_from_path, get_workspace_service_by_id_from_path, get_user_resource_by_id_from_path

from db.repositories.operations import OperationRepository
from db.repositories.resources import ResourceRepository
from db.repositories.user_resources import UserResourceRepository
from db.repositories.workspaces import WorkspaceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from models.domain.resource import ResourceType, Resource
from models.domain.operation import Operation
from models.domain.workspace import WorkspaceRole
from models.schemas.operation import OperationInList, OperationInResponse
from models.schemas.user_resource import UserResourceInResponse, UserResourceIdInResponse, UserResourceInCreate, UserResourcesInList, UserResourcePatchEnabled
from models.schemas.workspace import WorkspaceInCreate, WorkspaceIdInResponse, WorkspacesInList, WorkspaceInResponse, WorkspacePatchEnabled
from models.schemas.workspace_service import WorkspaceServiceIdInResponse, WorkspaceServiceInCreate, WorkspaceServicesInList, WorkspaceServiceInResponse, WorkspaceServicePatchEnabled
from resources import strings
from service_bus.resource_request_sender import send_resource_request_message, RequestAction
from services.authentication import get_current_admin_user, \
    get_access_service, get_current_workspace_owner_user, get_current_workspace_owner_or_researcher_user, get_current_tre_user_or_tre_admin, get_current_workspace_owner_or_researcher_user_or_tre_admin
from services.authentication import extract_auth_information
from services.azure_resource_status import get_azure_resource_status

workspaces_core_router = APIRouter(dependencies=[Depends(get_current_tre_user_or_tre_admin)])
workspaces_shared_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_tre_admin)])
workspaces_workspace_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_researcher_user)])
workspace_services_workspace_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_researcher_user)])
user_resources_workspace_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_researcher_user)])


# HELPER FUNCTIONS
async def save_and_deploy_resource(resource, resource_repo, operations_repo) -> Operation:
    try:
        resource_repo.save_item(resource)
    except Exception as e:
        logging.error(f"Failed to save resource in DB: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        operation = await send_resource_request_message(resource, operations_repo, RequestAction.Install)
        return operation
    except Exception as e:
        resource_repo.delete_item(resource.id)
        logging.error(f"Failed send resource request message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE)


def validate_user_is_workspace_owner_or_resource_owner(user, user_resource):
    if "WorkspaceOwner" in user.roles:
        return

    if "WorkspaceResearcher" in user.roles and user_resource.ownerId == user.id:
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.ACCESS_USER_IS_NOT_OWNER_OR_RESEARCHER)


def get_user_role_assignments(user):
    access_service = get_access_service()
    return access_service.get_user_role_assignments(user.id)


def mark_resource_as_deleting(resource: Resource, resource_repo: ResourceRepository, resource_type: ResourceType) -> bool:
    try:
        return resource_repo.mark_resource_as_deleting(resource)
    except Exception as e:
        logging.error(f"Failed to delete {resource_type} instance in DB: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)


async def send_uninstall_message(resource: Resource, resource_repo: ResourceRepository, previous_deletion_status: bool, resource_type: ResourceType) -> Operation:
    try:
        operation = await send_resource_request_message(resource, RequestAction.UnInstall)
        return operation
    except Exception as e:
        resource_repo.restore_previous_deletion_state(resource, previous_deletion_status)
        logging.error(f"Failed send {resource_type} resource delete message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE)


# WORKSPACE ROUTES
@workspaces_core_router.get("/workspaces", response_model=WorkspacesInList, name=strings.API_GET_ALL_WORKSPACES)
async def retrieve_users_active_workspaces(request: Request, user=Depends(get_current_tre_user_or_tre_admin), workspace_repo=Depends(get_repository(WorkspaceRepository))) -> WorkspacesInList:

    try:
        user = await get_current_admin_user(request)
        return WorkspacesInList(workspaces=workspace_repo.get_active_workspaces())

    except Exception:
        workspaces = workspace_repo.get_active_workspaces()

        access_service = get_access_service()
        user_role_assignments = get_user_role_assignments(user)
        user_workspaces = [workspace for workspace in workspaces if access_service.get_workspace_role(user, workspace, user_role_assignments) != WorkspaceRole.NoRole]
        return WorkspacesInList(workspaces=user_workspaces)


@workspaces_shared_router.get("/workspaces/{workspace_id}", response_model=WorkspaceInResponse, name=strings.API_GET_WORKSPACE_BY_ID, dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_tre_admin)])
async def retrieve_workspace_by_workspace_id(workspace=Depends(get_workspace_by_id_from_path)) -> WorkspaceInResponse:
    return WorkspaceInResponse(workspace=workspace)


@workspaces_core_router.post("/workspaces", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_CREATE_WORKSPACE, dependencies=[Depends(get_current_admin_user)])
async def create_workspace(workspace_create: WorkspaceInCreate, workspace_repo=Depends(get_repository(WorkspaceRepository)), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInResponse:
    try:
        # TODO: This requires Directory.ReadAll ( Application.Read.All ) to be enabled in the Azure AD application to enable a users workspaces to be listed. This should be made optional.
        auth_info = extract_auth_information(workspace_create.properties["app_id"])
        workspace = workspace_repo.create_workspace_item(workspace_create, auth_info)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed to create workspace model instance: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    op = await save_and_deploy_resource(workspace, workspace_repo, operations_repo)
    operation = OperationInResponse(operation=op)

    return operation


@workspaces_core_router.patch("/workspaces/{workspace_id}", response_model=WorkspaceInResponse, name=strings.API_UPDATE_WORKSPACE, dependencies=[Depends(get_current_admin_user)])
async def patch_workspace(workspace_patch: WorkspacePatchEnabled, workspace=Depends(get_workspace_by_id_from_path), workspace_repo=Depends(get_repository(WorkspaceRepository))) -> WorkspaceInResponse:
    workspace_repo.patch_workspace(workspace, workspace_patch)
    return WorkspaceInResponse(workspace=workspace)


@workspaces_core_router.delete("/workspaces/{workspace_id}", response_model=WorkspaceIdInResponse, name=strings.API_DELETE_WORKSPACE, dependencies=[Depends(get_current_admin_user)])
async def delete_workspace(workspace=Depends(get_workspace_by_id_from_path), workspace_repo=Depends(get_repository(WorkspaceRepository)), workspace_service_repo=Depends(get_repository(WorkspaceServiceRepository))) -> WorkspaceIdInResponse:
    if workspace.is_enabled():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.WORKSPACE_NEEDS_TO_BE_DISABLED_BEFORE_DELETION)
    if len(workspace_service_repo.get_active_workspace_services_for_workspace(workspace.id)) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.WORKSPACE_SERVICES_NEED_TO_BE_DELETED_BEFORE_WORKSPACE)

    previous_deletion_status = mark_resource_as_deleting(workspace, workspace_repo, ResourceType.Workspace)
    await send_uninstall_message(workspace, workspace_repo, previous_deletion_status, ResourceType.Workspace)

    return WorkspaceIdInResponse(workspaceId=workspace.id)

# workspace operations
@workspaces_shared_router.get("/workspaces/{workspace_id}/operations", response_model=OperationInList, name=strings.API_GET_RESOURCE_OPERATIONS, dependencies=[Depends(get_current_admin_user)])
async def retrieve_workspace_operations_by_workspace_id(workspace=Depends(get_workspace_by_id_from_path), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInList:
    return OperationInList(operations=operations_repo.get_operations_by_resource_id(resource_id=workspace.id))

@workspaces_shared_router.get("/workspaces/{workspace_id}/operations/{operation_id}", response_model=OperationInResponse, name=strings.API_GET_RESOURCE_OPERATION_BY_ID, dependencies=[Depends(get_current_admin_user)])
async def retrieve_workspace_operation_by_workspace_id_and_operation_id(workspace=Depends(get_workspace_by_id_from_path), operation=Depends(get_operation_by_id_from_path)) -> OperationInList:
    return OperationInResponse(operation=operation)


# WORKSPACE SERVICES ROUTES
@workspace_services_workspace_router.get("/workspaces/{workspace_id}/workspace-services", response_model=WorkspaceServicesInList, name=strings.API_GET_ALL_WORKSPACE_SERVICES, dependencies=[Depends(get_current_workspace_owner_or_researcher_user)])
async def retrieve_users_active_workspace_services(workspace=Depends(get_workspace_by_id_from_path), workspace_services_repo=Depends(get_repository(WorkspaceServiceRepository))) -> WorkspaceServicesInList:
    workspace_services = workspace_services_repo.get_active_workspace_services_for_workspace(workspace.id)
    return WorkspaceServicesInList(workspaceServices=workspace_services)


@workspace_services_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}", response_model=WorkspaceServiceInResponse, name=strings.API_GET_WORKSPACE_SERVICE_BY_ID, dependencies=[Depends(get_current_workspace_owner_or_researcher_user), Depends(get_workspace_by_id_from_path)])
async def retrieve_workspace_service_by_id(workspace_service=Depends(get_workspace_service_by_id_from_path)) -> WorkspaceServiceInResponse:
    return WorkspaceServiceInResponse(workspaceService=workspace_service)


@workspace_services_workspace_router.post("/workspaces/{workspace_id}/workspace-services", status_code=status.HTTP_202_ACCEPTED, response_model=WorkspaceServiceIdInResponse, name=strings.API_CREATE_WORKSPACE_SERVICE, dependencies=[Depends(get_current_workspace_owner_user)])
async def create_workspace_service(workspace_service_input: WorkspaceServiceInCreate, workspace_service_repo=Depends(get_repository(WorkspaceServiceRepository)), operations_repo=Depends(get_repository(OperationRepository)), workspace=Depends(get_deployed_workspace_by_id_from_path)) -> WorkspaceServiceIdInResponse:

    try:
        workspace_service = workspace_service_repo.create_workspace_service_item(workspace_service_input, workspace.id)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed create workspace service model instance: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await save_and_deploy_resource(workspace_service, workspace_service_repo, operations_repo)

    return WorkspaceServiceIdInResponse(workspaceServiceId=workspace_service.id)


@workspace_services_workspace_router.patch("/workspaces/{workspace_id}/workspace-services/{service_id}", response_model=WorkspaceServiceInResponse, name=strings.API_UPDATE_WORKSPACE_SERVICE, dependencies=[Depends(get_current_workspace_owner_or_researcher_user), Depends(get_workspace_by_id_from_path)])
async def patch_workspace_service(workspace_service_patch: WorkspaceServicePatchEnabled, workspace_service_repo=Depends(get_repository(WorkspaceServiceRepository)), workspace_service=Depends(get_workspace_service_by_id_from_path)) -> WorkspaceServiceInResponse:
    workspace_service_repo.patch_workspace_service(workspace_service, workspace_service_patch)
    return WorkspaceServiceInResponse(workspaceService=workspace_service)


@workspace_services_workspace_router.delete("/workspaces/{workspace_id}/workspace-services/{service_id}", response_model=WorkspaceServiceIdInResponse, name=strings.API_DELETE_WORKSPACE_SERVICE, dependencies=[Depends(get_current_workspace_owner_user)])
async def delete_workspace_service(workspace=Depends(get_workspace_by_id_from_path), workspace_service=Depends(get_workspace_service_by_id_from_path), workspace_service_repo=Depends(get_repository(WorkspaceServiceRepository)), user_resource_repo=Depends(get_repository(UserResourceRepository))) -> WorkspaceServiceIdInResponse:

    if workspace_service.is_enabled():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.WORKSPACE_SERVICE_NEEDS_TO_BE_DISABLED_BEFORE_DELETION)

    if len(user_resource_repo.get_user_resources_for_workspace_service(workspace.id, workspace_service.id)) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.USER_RESOURCES_NEED_TO_BE_DELETED_BEFORE_WORKSPACE)

    previous_deletion_status = mark_resource_as_deleting(workspace_service, workspace_service_repo, ResourceType.WorkspaceService)
    await send_uninstall_message(workspace_service, workspace_service_repo, previous_deletion_status, ResourceType.WorkspaceService)

    return WorkspaceServiceIdInResponse(workspaceServiceId=workspace_service.id)

# workspace service operations
@workspace_services_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}/operations", response_model=OperationInList, name=strings.API_GET_RESOURCE_OPERATIONS, dependencies=[Depends(get_current_workspace_owner_or_researcher_user), Depends(get_workspace_by_id_from_path)])
async def retrieve_workspace_service_operations_by_workspace_service_id(workspace_service=Depends(get_workspace_service_by_id_from_path), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInList:
    return OperationInList(operations_repo.get_operations_by_resource_id(resource_id=workspace_service.id))

@workspace_services_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}/operations/{operation_id}", response_model=OperationInResponse, name=strings.API_GET_RESOURCE_OPERATION_BY_ID, dependencies=[Depends(get_current_workspace_owner_or_researcher_user), Depends(get_workspace_by_id_from_path)])
async def retrieve_workspace_service_operation_by_workspace_service_id_and_operation_id(workspace_service=Depends(get_workspace_service_by_id_from_path), operation=Depends(get_operation_by_id_from_path)) -> OperationInList:
    return OperationInResponse(operation=operation)


# USER RESOURCE ROUTES
@user_resources_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources", response_model=UserResourcesInList, name=strings.API_GET_MY_USER_RESOURCES, dependencies=[Depends(get_workspace_by_id_from_path)])
async def retrieve_user_resources_for_workspace_service(workspace_id: str, service_id: str, user=Depends(get_current_workspace_owner_or_researcher_user), user_resource_repo=Depends(get_repository(UserResourceRepository))) -> UserResourcesInList:
    user_resources = user_resource_repo.get_user_resources_for_workspace_service(workspace_id, service_id)

    # filter only to the user - for researchers
    if "WorkspaceResearcher" in user.roles and "WorkspaceOwner" not in user.roles:
        user_resources = [resource for resource in user_resources if resource.ownerId == user.id]

    for user_resource in user_resources:
        if 'azure_resource_id' in user_resource.properties:
            user_resource.azureStatus = get_azure_resource_status(user_resource.properties['azure_resource_id'])

    return UserResourcesInList(userResources=user_resources)


@user_resources_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}", response_model=UserResourceInResponse, name=strings.API_GET_USER_RESOURCE, dependencies=[Depends(get_workspace_by_id_from_path)])
async def retrieve_user_resource_by_id(user_resource=Depends(get_user_resource_by_id_from_path), user=Depends(get_current_workspace_owner_or_researcher_user)) -> UserResourceInResponse:
    validate_user_is_workspace_owner_or_resource_owner(user, user_resource)

    if 'azure_resource_id' in user_resource.properties:
        user_resource.azureStatus = get_azure_resource_status(user_resource.properties['azure_resource_id'])

    return UserResourceInResponse(userResource=user_resource)


@user_resources_workspace_router.post("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources", status_code=status.HTTP_202_ACCEPTED, response_model=UserResourceIdInResponse, name=strings.API_CREATE_USER_RESOURCE)
async def create_user_resource(user_resource_create: UserResourceInCreate, user_resource_repo=Depends(get_repository(UserResourceRepository)), operations_repo=Depends(get_repository(OperationRepository)), user=Depends(get_current_workspace_owner_or_researcher_user), workspace=Depends(get_deployed_workspace_by_id_from_path), workspace_service=Depends(get_deployed_workspace_service_by_id_from_path)) -> UserResourceIdInResponse:

    try:
        user_resource = user_resource_repo.create_user_resource_item(user_resource_create, workspace.id, workspace_service.id, workspace_service.templateName, user.id)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed create user resource model instance: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await save_and_deploy_resource(user_resource, user_resource_repo, operations_repo)

    return UserResourceIdInResponse(resourceId=user_resource.id)


@user_resources_workspace_router.delete("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}", response_model=UserResourceIdInResponse, name=strings.API_DELETE_USER_RESOURCE)
async def delete_user_resource(user=Depends(get_current_workspace_owner_or_researcher_user), user_resource=Depends(get_user_resource_by_id_from_path), user_resource_repo=Depends(get_repository(UserResourceRepository))) -> UserResourceIdInResponse:
    validate_user_is_workspace_owner_or_resource_owner(user, user_resource)

    if user_resource.is_enabled():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.USER_RESOURCE_NEEDS_TO_BE_DISABLED_BEFORE_DELETION)

    previous_deletion_status = mark_resource_as_deleting(user_resource, user_resource_repo, ResourceType.UserResource)
    await send_uninstall_message(user_resource, user_resource_repo, previous_deletion_status, ResourceType.UserResource)

    return UserResourceIdInResponse(resourceId=user_resource.id)


@user_resources_workspace_router.patch("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}", response_model=UserResourceInResponse, name=strings.API_UPDATE_USER_RESOURCE, dependencies=[Depends(get_workspace_by_id_from_path), Depends(get_workspace_service_by_id_from_path)])
async def patch_user_resource(user_resource_patch: UserResourcePatchEnabled, user=Depends(get_current_workspace_owner_or_researcher_user), user_resource=Depends(get_user_resource_by_id_from_path), user_resource_repo=Depends(get_repository(UserResourceRepository))) -> UserResourceInResponse:
    validate_user_is_workspace_owner_or_resource_owner(user, user_resource)
    user_resource_repo.patch_user_resource(user_resource, user_resource_patch)
    return UserResourceInResponse(userResource=user_resource)

# user resource operations
@workspace_services_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}/operations", response_model=OperationInList, name=strings.API_GET_RESOURCE_OPERATIONS, dependencies=[Depends(get_workspace_by_id_from_path)])
async def retrieve_workspace_service_operations_by_workspace_service_id(user_resource=Depends(get_user_resource_by_id_from_path), user=Depends(get_current_workspace_owner_or_researcher_user), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInList:
    validate_user_is_workspace_owner_or_resource_owner(user, user_resource)
    return OperationInList(operations_repo.get_operations_by_resource_id(resource_id=user_resource.id))

@workspace_services_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}/operations/{operation_id}", response_model=OperationInResponse, name=strings.API_GET_RESOURCE_OPERATION_BY_ID, dependencies=[Depends(get_workspace_by_id_from_path)])
async def retrieve_workspace_service_operation_by_workspace_service_id_and_operation_id(user_resource=Depends(get_user_resource_by_id_from_path), user=Depends(get_current_workspace_owner_or_researcher_user), operation=Depends(get_operation_by_id_from_path)) -> OperationInList:
    validate_user_is_workspace_owner_or_resource_owner(user, user_resource)
    return OperationInResponse(operation=operation)
