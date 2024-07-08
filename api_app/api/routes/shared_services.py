import asyncio

from fastapi import APIRouter, Depends, HTTPException, Header, status, Response
from jsonschema.exceptions import ValidationError

from db.repositories.operations import OperationRepository
from db.errors import DuplicateEntity, MajorVersionUpdateDenied, UserNotAuthorizedToUseTemplate, TargetTemplateVersionDoesNotExist, VersionDowngradeDenied
from api.helpers import get_repository
from api.dependencies.shared_services import get_shared_service_by_id_from_path, get_operation_by_id_from_path
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources_history import ResourceHistoryRepository
from db.repositories.shared_services import SharedServiceRepository
from models.domain.resource import ResourceType
from models.schemas.operation import OperationInList, OperationInResponse
from models.schemas.shared_service import RestrictedSharedServiceInResponse, RestrictedSharedServicesInList, SharedServiceInCreate, SharedServicesInList, SharedServiceInResponse
from models.schemas.resource import ResourceHistoryInList, ResourcePatch
from resources import strings
from .workspaces import save_and_deploy_resource, construct_location_header
from azure.cosmos.exceptions import CosmosAccessConditionFailedError
from .resource_helpers import enrich_resource_with_available_upgrades, send_custom_action_message, send_uninstall_message, send_resource_request_message
from services.authentication import get_current_admin_user, get_current_tre_user_or_tre_admin
from models.domain.request_action import RequestAction
from services.logging import logger


shared_services_router = APIRouter(dependencies=[Depends(get_current_tre_user_or_tre_admin)])


def user_is_tre_admin(user):
    if "TREAdmin" in user.roles:
        return True
    return False


@shared_services_router.get("/shared-services", response_model=SharedServicesInList, name=strings.API_GET_ALL_SHARED_SERVICES, dependencies=[Depends(get_current_tre_user_or_tre_admin)])
async def retrieve_shared_services(shared_services_repo=Depends(get_repository(SharedServiceRepository)), user=Depends(get_current_tre_user_or_tre_admin), resource_template_repo=Depends(get_repository(ResourceTemplateRepository))) -> SharedServicesInList:
    shared_services = await shared_services_repo.get_active_shared_services()
    await asyncio.gather(*[enrich_resource_with_available_upgrades(shared_service, resource_template_repo) for shared_service in shared_services])
    if user_is_tre_admin(user):
        return SharedServicesInList(sharedServices=shared_services)
    else:
        return RestrictedSharedServicesInList(sharedServices=shared_services)


@shared_services_router.get("/shared-services/{shared_service_id}", response_model=SharedServiceInResponse, name=strings.API_GET_SHARED_SERVICE_BY_ID, dependencies=[Depends(get_current_tre_user_or_tre_admin), Depends(get_shared_service_by_id_from_path)])
async def retrieve_shared_service_by_id(shared_service=Depends(get_shared_service_by_id_from_path), user=Depends(get_current_tre_user_or_tre_admin), resource_template_repo=Depends(get_repository(ResourceTemplateRepository))):
    await enrich_resource_with_available_upgrades(shared_service, resource_template_repo)
    if user_is_tre_admin(user):
        return SharedServiceInResponse(sharedService=shared_service)
    else:
        return RestrictedSharedServiceInResponse(sharedService=shared_service)


@shared_services_router.post("/shared-services", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_CREATE_SHARED_SERVICE, dependencies=[Depends(get_current_admin_user)])
async def create_shared_service(response: Response, shared_service_input: SharedServiceInCreate, user=Depends(get_current_admin_user), shared_services_repo=Depends(get_repository(SharedServiceRepository)), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), operations_repo=Depends(get_repository(OperationRepository)), resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> OperationInResponse:
    try:
        shared_service, resource_template = await shared_services_repo.create_shared_service_item(shared_service_input, user.roles)
    except (ValidationError, ValueError) as e:
        logger.exception("Failed create shared service model instance")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DuplicateEntity as e:
        logger.exception("Shared service already exists")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except UserNotAuthorizedToUseTemplate as e:
        logger.exception("User not authorized to use template")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    operation = await save_and_deploy_resource(
        resource=shared_service,
        resource_repo=shared_services_repo,
        operations_repo=operations_repo,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user,
        resource_template=resource_template)
    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


@shared_services_router.patch("/shared-services/{shared_service_id}",
                              status_code=status.HTTP_202_ACCEPTED,
                              response_model=OperationInResponse,
                              name=strings.API_UPDATE_SHARED_SERVICE,
                              dependencies=[Depends(get_current_admin_user), Depends(get_shared_service_by_id_from_path)])
async def patch_shared_service(shared_service_patch: ResourcePatch, response: Response, user=Depends(get_current_admin_user), shared_service_repo=Depends(get_repository(SharedServiceRepository)), resource_history_repo=Depends(get_repository(ResourceHistoryRepository)), shared_service=Depends(get_shared_service_by_id_from_path), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), operations_repo=Depends(get_repository(OperationRepository)), etag: str = Header(...), force_version_update: bool = False) -> SharedServiceInResponse:
    try:
        patched_shared_service, _ = await shared_service_repo.patch_shared_service(shared_service, shared_service_patch, etag, resource_template_repo, resource_history_repo, user, force_version_update)
        operation = await send_resource_request_message(
            resource=patched_shared_service,
            operations_repo=operations_repo,
            resource_repo=shared_service_repo,
            user=user,
            resource_template_repo=resource_template_repo,
            resource_history_repo=resource_history_repo,
            action=RequestAction.Upgrade)

        response.headers["Location"] = construct_location_header(operation)
        return OperationInResponse(operation=operation)
    except CosmosAccessConditionFailedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.ETAG_CONFLICT)
    except ValidationError as v:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=v.message)
    except (MajorVersionUpdateDenied, TargetTemplateVersionDoesNotExist, VersionDowngradeDenied) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@shared_services_router.delete("/shared-services/{shared_service_id}", response_model=OperationInResponse, name=strings.API_DELETE_SHARED_SERVICE, dependencies=[Depends(get_current_admin_user)])
async def delete_shared_service(response: Response, user=Depends(get_current_admin_user), shared_service=Depends(get_shared_service_by_id_from_path), operations_repo=Depends(get_repository(OperationRepository)), shared_service_repo=Depends(get_repository(SharedServiceRepository)), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> OperationInResponse:
    if shared_service.isEnabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.SHARED_SERVICE_NEEDS_TO_BE_DISABLED_BEFORE_DELETION)

    operation = await send_uninstall_message(
        resource=shared_service,
        resource_repo=shared_service_repo,
        operations_repo=operations_repo,
        resource_type=ResourceType.SharedService,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user)

    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


@shared_services_router.post("/shared-services/{shared_service_id}/invoke-action", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_INVOKE_ACTION_ON_SHARED_SERVICE, dependencies=[Depends(get_current_admin_user)])
async def invoke_action_on_shared_service(response: Response, action: str, user=Depends(get_current_admin_user), shared_service=Depends(get_shared_service_by_id_from_path), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), operations_repo=Depends(get_repository(OperationRepository)), shared_service_repo=Depends(get_repository(SharedServiceRepository)), resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> OperationInResponse:
    operation = await send_custom_action_message(
        resource=shared_service,
        resource_repo=shared_service_repo,
        custom_action=action,
        resource_type=ResourceType.SharedService,
        operations_repo=operations_repo,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user)

    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


# Shared service operations
@shared_services_router.get("/shared-services/{shared_service_id}/operations", response_model=OperationInList, name=strings.API_GET_RESOURCE_OPERATIONS, dependencies=[Depends(get_current_admin_user), Depends(get_shared_service_by_id_from_path)])
async def retrieve_shared_service_operations_by_shared_service_id(shared_service=Depends(get_shared_service_by_id_from_path), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInList:
    return OperationInList(operations=await operations_repo.get_operations_by_resource_id(resource_id=shared_service.id))


@shared_services_router.get("/shared-services/{shared_service_id}/operations/{operation_id}", response_model=OperationInResponse, name=strings.API_GET_RESOURCE_OPERATION_BY_ID, dependencies=[Depends(get_current_admin_user), Depends(get_shared_service_by_id_from_path)])
async def retrieve_shared_service_operation_by_shared_service_id_and_operation_id(shared_service=Depends(get_shared_service_by_id_from_path), operation=Depends(get_operation_by_id_from_path)) -> OperationInResponse:
    return OperationInResponse(operation=operation)


# Shared service history
@shared_services_router.get("/shared-services/{shared_service_id}/history", response_model=ResourceHistoryInList, name=strings.API_GET_RESOURCE_HISTORY, dependencies=[Depends(get_current_admin_user)])
async def retrieve_shared_service_history_by_shared_service_id(shared_service=Depends(get_shared_service_by_id_from_path), resource_history_repo=Depends(get_repository(ResourceHistoryRepository))) -> ResourceHistoryInList:
    return ResourceHistoryInList(resource_history=await resource_history_repo.get_resource_history_by_resource_id(resource_id=shared_service.id))
