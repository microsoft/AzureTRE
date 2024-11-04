import asyncio

from fastapi import APIRouter, Depends, HTTPException, Header, status, Request, Response

from jsonschema.exceptions import ValidationError

from api.helpers import get_repository
from api.dependencies.workspaces import get_operation_by_id_from_path, get_workspace_by_id_from_path, get_deployed_workspace_by_id_from_path, get_deployed_workspace_service_by_id_from_path, get_workspace_service_by_id_from_path, get_user_resource_by_id_from_path
from db.errors import InvalidInput, MajorVersionUpdateDenied, TargetTemplateVersionDoesNotExist, UserNotAuthorizedToUseTemplate, VersionDowngradeDenied
from db.repositories.operations import OperationRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources_history import ResourceHistoryRepository
from db.repositories.user_resources import UserResourceRepository
from db.repositories.workspaces import WorkspaceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from models.domain.resource import ResourceType
from models.domain.workspace import WorkspaceAuth, WorkspaceRole
from models.schemas.operation import OperationInList, OperationInResponse
from models.schemas.user_resource import UserResourceInResponse, UserResourceInCreate, UserResourcesInList
from models.schemas.workspace import WorkspaceAuthInResponse, WorkspaceInCreate, WorkspacesInList, WorkspaceInResponse
from models.schemas.workspace_service import WorkspaceServiceInCreate, WorkspaceServicesInList, WorkspaceServiceInResponse
from models.schemas.resource import ResourceHistoryInList, ResourcePatch
from models.schemas.resource_template import ResourceTemplateInformationInList
from models.schemas.users import UsersInResponse
from resources import strings
from services.access_service import AuthConfigValidationError
from services.authentication import get_current_admin_user, \
    get_access_service, get_current_workspace_owner_user, get_current_workspace_owner_or_researcher_user, get_current_tre_user_or_tre_admin, \
    get_current_workspace_owner_or_tre_admin, \
    get_current_workspace_owner_or_researcher_user_or_airlock_manager, \
    get_current_workspace_owner_or_airlock_manager, \
    get_current_workspace_owner_or_researcher_user_or_airlock_manager_or_tre_admin
from services.authentication import extract_auth_information
from services.azure_resource_status import get_azure_resource_status
from azure.cosmos.exceptions import CosmosAccessConditionFailedError
from .resource_helpers import cascaded_update_resource, delete_validation, enrich_resource_with_available_upgrades, get_identity_role_assignments, save_and_deploy_resource, construct_location_header, send_uninstall_message, \
    send_custom_action_message, send_resource_request_message, update_user_resource
from models.domain.request_action import RequestAction
from services.logging import logger


workspaces_core_router = APIRouter(dependencies=[Depends(get_current_tre_user_or_tre_admin)])
workspaces_shared_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager_or_tre_admin)])
workspace_services_workspace_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager)])
user_resources_workspace_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager)])


def validate_user_has_valid_role_for_user_resource(user, user_resource):
    if "WorkspaceOwner" in user.roles:
        return

    if ("WorkspaceResearcher" in user.roles or "AirlockManager" in user.roles) and user_resource.ownerId == user.id:
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.ACCESS_USER_IS_NOT_OWNER_OR_RESEARCHER)


# WORKSPACE ROUTES
@workspaces_core_router.get("/workspaces", response_model=WorkspacesInList, name=strings.API_GET_ALL_WORKSPACES)
async def retrieve_users_active_workspaces(request: Request, user=Depends(get_current_tre_user_or_tre_admin), workspace_repo=Depends(get_repository(WorkspaceRepository)), resource_template_repo=Depends(get_repository(ResourceTemplateRepository))) -> WorkspacesInList:

    try:
        user = await get_current_admin_user(request)
        workspaces = await workspace_repo.get_active_workspaces()
        await asyncio.gather(*[enrich_resource_with_available_upgrades(workspace, resource_template_repo) for workspace in workspaces])
        return WorkspacesInList(workspaces=workspaces)

    except Exception:
        workspaces = await workspace_repo.get_active_workspaces()

        access_service = get_access_service()
        user_role_assignments = get_identity_role_assignments(user)

        def _safe_get_workspace_role(user, workspace, user_role_assignments):
            # provide graceful failure if there is a workspace without auth info
            # to prevent it blocking listing other workspaces
            try:
                return access_service.get_workspace_role(user, workspace, user_role_assignments)
            except AuthConfigValidationError:
                return WorkspaceRole.NoRole
        user_workspaces = [workspace for workspace in workspaces if _safe_get_workspace_role(user, workspace, user_role_assignments) != WorkspaceRole.NoRole]
        await asyncio.gather(*[enrich_resource_with_available_upgrades(workspace, resource_template_repo) for workspace in user_workspaces])
        return WorkspacesInList(workspaces=user_workspaces)


@workspaces_shared_router.get("/workspaces/{workspace_id}", response_model=WorkspaceInResponse, name=strings.API_GET_WORKSPACE_BY_ID)
async def retrieve_workspace_by_workspace_id(workspace=Depends(get_workspace_by_id_from_path), resource_template_repo=Depends(get_repository(ResourceTemplateRepository))) -> WorkspaceInResponse:
    await enrich_resource_with_available_upgrades(workspace, resource_template_repo)
    return WorkspaceInResponse(workspace=workspace)


@workspaces_core_router.get("/workspaces/{workspace_id}/scopeid", response_model=WorkspaceAuthInResponse, name=strings.API_GET_WORKSPACE_SCOPE_ID_BY_WORKSPACE_ID)
async def retrieve_workspace_scope_id_by_workspace_id(workspace=Depends(get_workspace_by_id_from_path)) -> WorkspaceAuthInResponse:
    wsAuth = WorkspaceAuth()
    if "scope_id" in workspace.properties:
        wsAuth.scopeId = workspace.properties["scope_id"]
    return WorkspaceAuthInResponse(workspaceAuth=wsAuth)


@workspaces_core_router.post("/workspaces", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_CREATE_WORKSPACE, dependencies=[Depends(get_current_admin_user)])
async def create_workspace(workspace_create: WorkspaceInCreate, response: Response, user=Depends(get_current_admin_user), workspace_repo=Depends(get_repository(WorkspaceRepository)), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), operations_repo=Depends(get_repository(OperationRepository)), resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> OperationInResponse:
    try:
        # TODO: This requires Directory.ReadAll ( Application.Read.All ) to be enabled in the Azure AD application to enable a users workspaces to be listed. This should be made optional.
        auth_info = extract_auth_information(workspace_create.properties)
        workspace, resource_template = await workspace_repo.create_workspace_item(workspace_create, auth_info, user.id, user.roles)
    except (ValidationError, ValueError) as e:
        logger.exception("Failed to create workspace model instance")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UserNotAuthorizedToUseTemplate as e:
        logger.exception("User not authorized to use template")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except InvalidInput as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    operation = await save_and_deploy_resource(
        resource=workspace,
        resource_repo=workspace_repo,
        operations_repo=operations_repo,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user,
        resource_template=resource_template)
    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


@workspaces_core_router.patch("/workspaces/{workspace_id}", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_UPDATE_WORKSPACE, dependencies=[Depends(get_current_admin_user)])
async def patch_workspace(resource_patch: ResourcePatch, response: Response, user=Depends(get_current_admin_user), workspace=Depends(get_workspace_by_id_from_path), workspace_repo: WorkspaceRepository = Depends(get_repository(WorkspaceRepository)), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), operations_repo=Depends(get_repository(OperationRepository)), resource_history_repo=Depends(get_repository(ResourceHistoryRepository)), etag: str = Header(...), force_version_update: bool = False) -> OperationInResponse:
    try:
        is_disablement = resource_patch.isEnabled is not None and not resource_patch.isEnabled
        if is_disablement:
            await cascaded_update_resource(resource_patch, workspace, user, force_version_update, resource_template_repo=resource_template_repo, resource_history_repo=resource_history_repo, resource_repo=workspace_repo)
        patched_workspace, _ = await workspace_repo.patch_workspace(workspace, resource_patch, etag, resource_template_repo, resource_history_repo, user, force_version_update)
        # Send the message to service bus
        operation = await send_resource_request_message(
            resource=patched_workspace,
            operations_repo=operations_repo,
            resource_repo=workspace_repo,
            user=user,
            resource_template_repo=resource_template_repo,
            resource_history_repo=resource_history_repo,
            action=RequestAction.Upgrade,
            is_cascade=is_disablement)

        response.headers["Location"] = construct_location_header(operation)
        return OperationInResponse(operation=operation)
    except CosmosAccessConditionFailedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.ETAG_CONFLICT)
    except ValidationError as v:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=v.message)
    except (MajorVersionUpdateDenied, TargetTemplateVersionDoesNotExist, VersionDowngradeDenied) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@workspaces_core_router.delete("/workspaces/{workspace_id}", response_model=OperationInResponse, name=strings.API_DELETE_WORKSPACE, dependencies=[Depends(get_current_admin_user)])
async def delete_workspace(response: Response, user=Depends(get_current_admin_user), workspace=Depends(get_workspace_by_id_from_path), operations_repo=Depends(get_repository(OperationRepository)), workspace_repo=Depends(get_repository(WorkspaceRepository)), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> OperationInResponse:
    if await delete_validation(workspace, workspace_repo):
        operation = await send_uninstall_message(
            resource=workspace,
            resource_repo=workspace_repo,
            operations_repo=operations_repo,
            resource_type=ResourceType.Workspace,
            resource_template_repo=resource_template_repo,
            resource_history_repo=resource_history_repo,
            user=user,
            is_cascade=True
        )

        response.headers["Location"] = construct_location_header(operation)
        return OperationInResponse(operation=operation)


@workspaces_core_router.post("/workspaces/{workspace_id}/invoke-action", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_INVOKE_ACTION_ON_WORKSPACE, dependencies=[Depends(get_current_admin_user)])
async def invoke_action_on_workspace(response: Response, action: str, user=Depends(get_current_admin_user), workspace=Depends(get_workspace_by_id_from_path), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), operations_repo=Depends(get_repository(OperationRepository)), workspace_repo=Depends(get_repository(WorkspaceRepository)), resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> OperationInResponse:
    operation = await send_custom_action_message(
        resource=workspace,
        resource_repo=workspace_repo,
        custom_action=action,
        resource_type=ResourceType.Workspace,
        operations_repo=operations_repo,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user)

    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


@workspaces_shared_router.get("/workspaces/{workspace_id}/users", response_model=UsersInResponse, name=strings.API_GET_WORKSPACE_USERS)
async def get_workspace_users(workspace=Depends(get_workspace_by_id_from_path)) -> UsersInResponse:
    access_service = get_access_service()
    users = access_service.get_workspace_users(workspace)
    return UsersInResponse(users=users)


# workspace operations
# This method only returns templates that the authenticated user is authorized to use
@workspaces_shared_router.get("/workspaces/{workspace_id}/workspace-service-templates", response_model=ResourceTemplateInformationInList, name=strings.API_GET_WORKSPACE_SERVICE_TEMPLATES_IN_WORKSPACE)
async def get_workspace_service_templates(
        workspace=Depends(get_workspace_by_id_from_path),
        template_repo=Depends(get_repository(ResourceTemplateRepository)),
        user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager_or_tre_admin)) -> ResourceTemplateInformationInList:
    template_infos = await template_repo.get_templates_information(ResourceType.WorkspaceService, user.roles)
    return ResourceTemplateInformationInList(templates=template_infos)


# This method only returns templates that the authenticated user is authorized to use
@workspaces_shared_router.get("/workspaces/{workspace_id}/workspace-service-templates/{service_template_name}/user-resource-templates", response_model=ResourceTemplateInformationInList, name=strings.API_GET_USER_RESOURCE_TEMPLATES_IN_WORKSPACE)
async def get_user_resource_templates(
        service_template_name: str,
        workspace=Depends(get_workspace_by_id_from_path),
        template_repo=Depends(get_repository(ResourceTemplateRepository)),
        user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager_or_tre_admin)) -> ResourceTemplateInformationInList:
    template_infos = await template_repo.get_templates_information(ResourceType.UserResource, user.roles, service_template_name)
    return ResourceTemplateInformationInList(templates=template_infos)


@workspaces_shared_router.get("/workspaces/{workspace_id}/operations", response_model=OperationInList, name=strings.API_GET_RESOURCE_OPERATIONS, dependencies=[Depends(get_current_workspace_owner_or_tre_admin)])
async def retrieve_workspace_operations_by_workspace_id(workspace=Depends(get_workspace_by_id_from_path), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInList:
    return OperationInList(operations=await operations_repo.get_operations_by_resource_id(resource_id=workspace.id))


@workspaces_shared_router.get("/workspaces/{workspace_id}/operations/{operation_id}", response_model=OperationInResponse, name=strings.API_GET_RESOURCE_OPERATION_BY_ID, dependencies=[Depends(get_current_workspace_owner_or_tre_admin)])
async def retrieve_workspace_operation_by_workspace_id_and_operation_id(workspace=Depends(get_workspace_by_id_from_path), operation=Depends(get_operation_by_id_from_path)) -> OperationInList:
    return OperationInResponse(operation=operation)


@workspaces_shared_router.get("/workspaces/{workspace_id}/history", response_model=ResourceHistoryInList, name=strings.API_GET_RESOURCE_HISTORY, dependencies=[Depends(get_current_workspace_owner_or_tre_admin)])
async def retrieve_workspace_history_by_workspace_id(workspace=Depends(get_workspace_by_id_from_path), resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> ResourceHistoryInList:
    return ResourceHistoryInList(resource_history=await resource_history_repo.get_resource_history_by_resource_id(resource_id=workspace.id))


# WORKSPACE SERVICES ROUTES
@workspace_services_workspace_router.get("/workspaces/{workspace_id}/workspace-services", response_model=WorkspaceServicesInList, name=strings.API_GET_ALL_WORKSPACE_SERVICES, dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager)])
async def retrieve_users_active_workspace_services(workspace=Depends(get_workspace_by_id_from_path), workspace_services_repo=Depends(get_repository(WorkspaceServiceRepository)), resource_template_repo=Depends(get_repository(ResourceTemplateRepository))) -> WorkspaceServicesInList:
    workspace_services = await workspace_services_repo.get_active_workspace_services_for_workspace(workspace.id)
    await asyncio.gather(*[enrich_resource_with_available_upgrades(workspace_service, resource_template_repo) for workspace_service in workspace_services])
    return WorkspaceServicesInList(workspaceServices=workspace_services)


@workspace_services_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}", response_model=WorkspaceServiceInResponse, name=strings.API_GET_WORKSPACE_SERVICE_BY_ID, dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager), Depends(get_workspace_by_id_from_path)])
async def retrieve_workspace_service_by_id(workspace_service=Depends(get_workspace_service_by_id_from_path), resource_template_repo=Depends(get_repository(ResourceTemplateRepository))) -> WorkspaceServiceInResponse:
    await enrich_resource_with_available_upgrades(workspace_service, resource_template_repo)
    return WorkspaceServiceInResponse(workspaceService=workspace_service)


@workspace_services_workspace_router.post("/workspaces/{workspace_id}/workspace-services", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_CREATE_WORKSPACE_SERVICE, dependencies=[Depends(get_current_workspace_owner_user)])
async def create_workspace_service(response: Response, workspace_service_input: WorkspaceServiceInCreate, user=Depends(get_current_workspace_owner_user), workspace_service_repo=Depends(get_repository(WorkspaceServiceRepository)), workspace_repo=Depends(get_repository(WorkspaceRepository)), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), operations_repo=Depends(get_repository(OperationRepository)), resource_history_repo=Depends(get_repository(ResourceHistoryRepository)), workspace=Depends(get_deployed_workspace_by_id_from_path)) -> OperationInResponse:

    try:
        workspace_service, resource_template = await workspace_service_repo.create_workspace_service_item(workspace_service_input, workspace.id, user.roles)
    except (ValidationError, ValueError) as e:
        logger.exception("Failed create workspace service model instance")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UserNotAuthorizedToUseTemplate as e:
        logger.exception("User not authorized to use template")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    # if template has address_space get an address space
    if resource_template.properties.get("address_space"):
        # check workspace has address_spaces property
        if not workspace.properties.get("address_spaces"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.WORKSPACE_DOES_NOT_HAVE_ADDRESS_SPACES_PROPERTY)
        workspace_service.properties["address_space"] = await workspace_repo.get_address_space_based_on_size(workspace_service_input.properties)
        workspace_patch = ResourcePatch()
        workspace_patch.properties = {"address_spaces": workspace.properties["address_spaces"] + [workspace_service.properties["address_space"]]}
        # IP address allocation is managed by the API. Ideally this request would happen as a result of the workspace
        # service deployment via the reosurce processor. there is no such functionality so the database is being
        # updated directly, and an "update" on the workspace is called by the workspace service pipeline.
        try:
            await workspace_repo.patch_workspace(workspace, workspace_patch, workspace.etag, resource_template_repo, resource_history_repo, user, False)
        except CosmosAccessConditionFailedError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.ETAG_CONFLICT)

    operation = await save_and_deploy_resource(
        resource=workspace_service,
        resource_repo=workspace_service_repo,
        operations_repo=operations_repo,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user,
        resource_template=resource_template)
    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


@workspace_services_workspace_router.patch("/workspaces/{workspace_id}/workspace-services/{service_id}", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_UPDATE_WORKSPACE_SERVICE, dependencies=[Depends(get_current_workspace_owner_or_researcher_user), Depends(get_workspace_by_id_from_path)])
async def patch_workspace_service(resource_patch: ResourcePatch, response: Response, user=Depends(get_current_workspace_owner_user), workspace_service_repo=Depends(get_repository(WorkspaceServiceRepository)), workspace_service=Depends(get_workspace_service_by_id_from_path), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), operations_repo=Depends(get_repository(OperationRepository)), resource_history_repo=Depends(get_repository(ResourceHistoryRepository)), etag: str = Header(...), force_version_update: bool = False) -> OperationInResponse:
    try:
        is_disablement = resource_patch.isEnabled is not None and not resource_patch.isEnabled
        if is_disablement:
            await cascaded_update_resource(resource_patch, workspace_service, user, force_version_update, resource_template_repo=resource_template_repo, resource_history_repo=resource_history_repo, resource_repo=workspace_service_repo)
        patched_workspace_service, _ = await workspace_service_repo.patch_workspace_service(workspace_service, resource_patch, etag, resource_template_repo, resource_history_repo, user, force_version_update)
        operation = await send_resource_request_message(
            resource=patched_workspace_service,
            operations_repo=operations_repo,
            resource_repo=workspace_service_repo,
            user=user,
            resource_template_repo=resource_template_repo,
            resource_history_repo=resource_history_repo,
            action=RequestAction.Upgrade,
            is_cascade=is_disablement)
        response.headers["Location"] = construct_location_header(operation)
        return OperationInResponse(operation=operation)
    except CosmosAccessConditionFailedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.ETAG_CONFLICT)
    except ValidationError as v:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=v.message)
    except (MajorVersionUpdateDenied, TargetTemplateVersionDoesNotExist, VersionDowngradeDenied) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@workspace_services_workspace_router.delete("/workspaces/{workspace_id}/workspace-services/{service_id}", response_model=OperationInResponse, name=strings.API_DELETE_WORKSPACE_SERVICE, dependencies=[Depends(get_current_workspace_owner_user)])
async def delete_workspace_service(response: Response, user=Depends(get_current_workspace_owner_user), workspace=Depends(get_workspace_by_id_from_path), workspace_service=Depends(get_workspace_service_by_id_from_path), workspace_service_repo=Depends(get_repository(WorkspaceServiceRepository)), user_resource_repo=Depends(get_repository(UserResourceRepository)), operations_repo=Depends(get_repository(OperationRepository)), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> OperationInResponse:
    if await delete_validation(workspace_service, workspace_service_repo):
        operation = await send_uninstall_message(
            resource=workspace_service,
            resource_repo=workspace_service_repo,
            operations_repo=operations_repo,
            resource_type=ResourceType.WorkspaceService,
            resource_template_repo=resource_template_repo,
            resource_history_repo=resource_history_repo,
            user=user,
            is_cascade=True)

        response.headers["Location"] = construct_location_header(operation)

        return OperationInResponse(operation=operation)


@workspace_services_workspace_router.post("/workspaces/{workspace_id}/workspace-services/{service_id}/invoke-action", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_INVOKE_ACTION_ON_WORKSPACE_SERVICE, dependencies=[Depends(get_current_workspace_owner_user)])
async def invoke_action_on_workspace_service(response: Response, action: str, user=Depends(get_current_workspace_owner_user), workspace_service=Depends(get_workspace_service_by_id_from_path), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), operations_repo=Depends(get_repository(OperationRepository)), workspace_service_repo=Depends(get_repository(WorkspaceServiceRepository)), resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> OperationInResponse:
    operation = await send_custom_action_message(
        resource=workspace_service,
        resource_repo=workspace_service_repo,
        custom_action=action,
        resource_type=ResourceType.WorkspaceService,
        operations_repo=operations_repo,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user)

    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


# workspace service operations
@workspace_services_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}/operations", response_model=OperationInList, name=strings.API_GET_RESOURCE_OPERATIONS, dependencies=[Depends(get_current_workspace_owner_or_airlock_manager), Depends(get_workspace_by_id_from_path)])
async def retrieve_workspace_service_operations_by_workspace_service_id(workspace_service=Depends(get_workspace_service_by_id_from_path), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInList:
    return OperationInList(operations=await operations_repo.get_operations_by_resource_id(resource_id=workspace_service.id))


@workspace_services_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}/operations/{operation_id}", response_model=OperationInResponse, name=strings.API_GET_RESOURCE_OPERATION_BY_ID, dependencies=[Depends(get_current_workspace_owner_or_airlock_manager), Depends(get_workspace_by_id_from_path)])
async def retrieve_workspace_service_operation_by_workspace_service_id_and_operation_id(workspace_service=Depends(get_workspace_service_by_id_from_path), operation=Depends(get_operation_by_id_from_path)) -> OperationInList:
    return OperationInResponse(operation=operation)


@workspace_services_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}/history", response_model=ResourceHistoryInList, name=strings.API_GET_RESOURCE_HISTORY, dependencies=[Depends(get_current_workspace_owner_or_airlock_manager), Depends(get_workspace_by_id_from_path)])
async def retrieve_workspace_service_history_by_workspace_service_id(workspace_service=Depends(get_workspace_service_by_id_from_path), resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> ResourceHistoryInList:
    return ResourceHistoryInList(resource_history=await resource_history_repo.get_resource_history_by_resource_id(resource_id=workspace_service.id))


# USER RESOURCE ROUTES
@user_resources_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources", response_model=UserResourcesInList, name=strings.API_GET_MY_USER_RESOURCES, dependencies=[Depends(get_workspace_by_id_from_path)])
async def retrieve_user_resources_for_workspace_service(
        workspace_id: str,
        service_id: str,
        user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager),
        resource_template_repo=Depends(get_repository(ResourceTemplateRepository)),
        user_resource_repo=Depends(get_repository(UserResourceRepository))) -> UserResourcesInList:
    user_resources = await user_resource_repo.get_user_resources_for_workspace_service(workspace_id, service_id)

    # filter only to the user - for researchers
    if ("WorkspaceResearcher" in user.roles or "AirlockManager" in user.roles) and "WorkspaceOwner" not in user.roles:
        user_resources = [resource for resource in user_resources if resource.ownerId == user.id]

    for user_resource in user_resources:
        if 'azure_resource_id' in user_resource.properties:
            user_resource.azureStatus = get_azure_resource_status(user_resource.properties['azure_resource_id'])

    await asyncio.gather(*[enrich_resource_with_available_upgrades(user_resource, resource_template_repo) for user_resource in user_resources])

    return UserResourcesInList(userResources=user_resources)


@user_resources_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}", response_model=UserResourceInResponse, name=strings.API_GET_USER_RESOURCE, dependencies=[Depends(get_workspace_by_id_from_path)])
async def retrieve_user_resource_by_id(
        user_resource=Depends(get_user_resource_by_id_from_path),
        resource_template_repo=Depends(get_repository(ResourceTemplateRepository)),
        user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager)) -> UserResourceInResponse:
    validate_user_has_valid_role_for_user_resource(user, user_resource)

    if 'azure_resource_id' in user_resource.properties:
        user_resource.azureStatus = get_azure_resource_status(user_resource.properties['azure_resource_id'])

    await enrich_resource_with_available_upgrades(user_resource, resource_template_repo)
    return UserResourceInResponse(userResource=user_resource)


@user_resources_workspace_router.post("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_CREATE_USER_RESOURCE)
async def create_user_resource(
        response: Response,
        user_resource_create: UserResourceInCreate,
        user_resource_repo=Depends(get_repository(UserResourceRepository)),
        resource_template_repo=Depends(get_repository(ResourceTemplateRepository)),
        operations_repo=Depends(get_repository(OperationRepository)),
        resource_history_repo=Depends(get_repository(ResourceHistoryRepository)),
        user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager),
        workspace=Depends(get_deployed_workspace_by_id_from_path),
        workspace_service=Depends(get_deployed_workspace_service_by_id_from_path)) -> OperationInResponse:

    try:
        user_resource, resource_template = await user_resource_repo.create_user_resource_item(user_resource_create, workspace.id, workspace_service.id, workspace_service.templateName, user.id, user.roles)
    except (ValidationError, ValueError) as e:
        logger.exception("Failed create user resource model instance")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UserNotAuthorizedToUseTemplate as e:
        logger.exception("User not authorized to use template")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    operation = await save_and_deploy_resource(
        resource=user_resource,
        resource_repo=user_resource_repo,
        operations_repo=operations_repo,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user,
        resource_template=resource_template)
    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


@user_resources_workspace_router.delete("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}", response_model=OperationInResponse, name=strings.API_DELETE_USER_RESOURCE)
async def delete_user_resource(
        response: Response,
        user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager),
        user_resource=Depends(get_user_resource_by_id_from_path),
        workspace_service=Depends(get_workspace_service_by_id_from_path),
        user_resource_repo=Depends(get_repository(UserResourceRepository)),
        operations_repo=Depends(get_repository(OperationRepository)),
        resource_template_repo=Depends(get_repository(ResourceTemplateRepository)),
        resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> OperationInResponse:
    validate_user_has_valid_role_for_user_resource(user, user_resource)

    if user_resource.isEnabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.USER_RESOURCE_NEEDS_TO_BE_DISABLED_BEFORE_DELETION)

    operation = await send_uninstall_message(
        resource=user_resource,
        resource_repo=user_resource_repo,
        operations_repo=operations_repo,
        resource_type=ResourceType.UserResource,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user)

    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


@user_resources_workspace_router.patch("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_UPDATE_USER_RESOURCE, dependencies=[Depends(get_workspace_by_id_from_path), Depends(get_workspace_service_by_id_from_path)])
async def patch_user_resource(
        user_resource_patch: ResourcePatch,
        response: Response,
        user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager),
        user_resource=Depends(get_user_resource_by_id_from_path),
        workspace_service=Depends(get_workspace_service_by_id_from_path),
        user_resource_repo=Depends(get_repository(UserResourceRepository)),
        resource_template_repo=Depends(get_repository(ResourceTemplateRepository)),
        resource_history_repo=Depends(get_repository(ResourceHistoryRepository)),
        operations_repo=Depends(get_repository(OperationRepository)),
        etag: str = Header(...),
        force_version_update: bool = False) -> OperationInResponse:
    validate_user_has_valid_role_for_user_resource(user, user_resource)

    try:
        operation = await update_user_resource(user_resource, user_resource_patch, force_version_update, user, etag, workspace_service, user_resource_repo, resource_template_repo, operations_repo, resource_history_repo)
        response.headers["Location"] = construct_location_header(operation)
        return OperationInResponse(operation=operation)
    except CosmosAccessConditionFailedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.ETAG_CONFLICT)
    except ValidationError as v:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=v.message)
    except (MajorVersionUpdateDenied, TargetTemplateVersionDoesNotExist, VersionDowngradeDenied) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# user resource actions
@user_resources_workspace_router.post("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}/invoke-action", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_INVOKE_ACTION_ON_USER_RESOURCE)
async def invoke_action_on_user_resource(
        response: Response,
        action: str,
        user_resource=Depends(get_user_resource_by_id_from_path),
        workspace_service=Depends(get_workspace_service_by_id_from_path),
        resource_template_repo=Depends(get_repository(ResourceTemplateRepository)),
        user_resource_repo=Depends(get_repository(UserResourceRepository)),
        operations_repo=Depends(get_repository(OperationRepository)),
        resource_history_repo=Depends(get_repository(ResourceHistoryRepository)),
        user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager)) -> OperationInResponse:
    validate_user_has_valid_role_for_user_resource(user, user_resource)
    operation = await send_custom_action_message(
        resource=user_resource,
        resource_repo=user_resource_repo,
        custom_action=action,
        resource_type=ResourceType.UserResource,
        operations_repo=operations_repo,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user,
        parent_service_name=workspace_service.templateName)

    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


# user resource operations
@user_resources_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}/operations", response_model=OperationInList, name=strings.API_GET_RESOURCE_OPERATIONS, dependencies=[Depends(get_workspace_by_id_from_path)])
async def retrieve_user_resource_operations_by_user_resource_id(
        user_resource=Depends(get_user_resource_by_id_from_path),
        user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager),
        operations_repo=Depends(get_repository(OperationRepository))) -> OperationInList:
    validate_user_has_valid_role_for_user_resource(user, user_resource)
    return OperationInList(operations=await operations_repo.get_operations_by_resource_id(resource_id=user_resource.id))


@user_resources_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}/operations/{operation_id}", response_model=OperationInResponse, name=strings.API_GET_RESOURCE_OPERATION_BY_ID, dependencies=[Depends(get_workspace_by_id_from_path)])
async def retrieve_user_resource_operations_by_user_resource_id_and_operation_id(
        user_resource=Depends(get_user_resource_by_id_from_path),
        user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager),
        operation=Depends(get_operation_by_id_from_path)) -> OperationInList:
    validate_user_has_valid_role_for_user_resource(user, user_resource)
    return OperationInResponse(operation=operation)


@user_resources_workspace_router.get("/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}/history", response_model=ResourceHistoryInList, name=strings.API_GET_RESOURCE_HISTORY, dependencies=[Depends(get_workspace_by_id_from_path)])
async def retrieve_user_resource_history_by_user_resource_id(user_resource=Depends(get_user_resource_by_id_from_path), user=Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager), resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> ResourceHistoryInList:
    validate_user_has_valid_role_for_user_resource(user, user_resource)
    return ResourceHistoryInList(resource_history=await resource_history_repo.get_resource_history_by_resource_id(resource_id=user_resource.id))
