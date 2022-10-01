import logging

from fastapi import APIRouter, Depends, HTTPException, Header, status, Response
from jsonschema.exceptions import ValidationError

from db.repositories.operations import OperationRepository
from db.errors import DuplicateEntity
from api.dependencies.database import get_repository
from api.dependencies.shared_services import get_shared_service_by_id_from_path, get_operation_by_id_from_path
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.shared_services import SharedServiceRepository
from models.domain.resource import ResourceType
from models.schemas.operation import OperationInList, OperationInResponse
from models.schemas.shared_service import RestrictedSharedServiceInResponse, SharedServiceInCreate, SharedServicesInList, SharedServiceInResponse
from models.schemas.resource import ResourcePatch
from resources import strings
from .workspaces import save_and_deploy_resource, construct_location_header
from azure.cosmos.exceptions import CosmosAccessConditionFailedError
from .resource_helpers import send_custom_action_message, send_uninstall_message, send_resource_request_message
from services.authentication import get_current_admin_user, get_current_tre_user_or_tre_admin
from models.domain.request_action import RequestAction


shared_services_router = APIRouter(dependencies=[Depends(get_current_tre_user_or_tre_admin)])


def user_is_tre_admin(user):
    if "TREAdmin" in user.roles:
        return True
    return False


@shared_services_router.get("/shared-services", response_model=SharedServicesInList, name=strings.API_GET_ALL_SHARED_SERVICES, dependencies=[Depends(get_current_tre_user_or_tre_admin)])
async def retrieve_shared_services(shared_services_repo=Depends(get_repository(SharedServiceRepository))) -> SharedServicesInList:
    shared_services = shared_services_repo.get_active_shared_services()
    return SharedServicesInList(sharedServices=shared_services)


@shared_services_router.get("/shared-services/{shared_service_id}", response_model=SharedServiceInResponse, name=strings.API_GET_SHARED_SERVICE_BY_ID, dependencies=[Depends(get_current_tre_user_or_tre_admin), Depends(get_shared_service_by_id_from_path)])
async def retrieve_shared_service_by_id(shared_service=Depends(get_shared_service_by_id_from_path), user=Depends(get_current_tre_user_or_tre_admin)):
    if user_is_tre_admin(user):
        return SharedServiceInResponse(sharedService=shared_service)
    else:
        return RestrictedSharedServiceInResponse(sharedService=shared_service)


@shared_services_router.post("/shared-services", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_CREATE_SHARED_SERVICE, dependencies=[Depends(get_current_admin_user)])
async def create_shared_service(response: Response, shared_service_input: SharedServiceInCreate, user=Depends(get_current_admin_user), shared_services_repo=Depends(get_repository(SharedServiceRepository)), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInResponse:
    try:
        shared_service, resource_template = shared_services_repo.create_shared_service_item(shared_service_input)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed create shared service model instance: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DuplicateEntity as e:
        logging.error(f"Shared service already exists: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    operation = await save_and_deploy_resource(
        resource=shared_service,
        resource_repo=shared_services_repo,
        operations_repo=operations_repo,
        resource_template_repo=resource_template_repo,
        user=user,
        resource_template=resource_template)
    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


@shared_services_router.patch("/shared-services/{shared_service_id}",
                              status_code=status.HTTP_202_ACCEPTED,
                              response_model=OperationInResponse,
                              name=strings.API_UPDATE_SHARED_SERVICE,
                              dependencies=[Depends(get_current_admin_user), Depends(get_shared_service_by_id_from_path)])
async def patch_shared_service(shared_service_patch: ResourcePatch, response: Response, user=Depends(get_current_admin_user), shared_service_repo=Depends(get_repository(SharedServiceRepository)), shared_service=Depends(get_shared_service_by_id_from_path), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), operations_repo=Depends(get_repository(OperationRepository)), etag: str = Header(...)) -> SharedServiceInResponse:
    try:
        patched_shared_service, resource_template = shared_service_repo.patch_shared_service(shared_service, shared_service_patch, etag, resource_template_repo, user)
        operation = await send_resource_request_message(
            resource=patched_shared_service,
            operations_repo=operations_repo,
            resource_repo=shared_service_repo,
            user=user,
            resource_template=resource_template,
            resource_template_repo=resource_template_repo,
            action=RequestAction.Upgrade)

        response.headers["Location"] = construct_location_header(operation)
        return OperationInResponse(operation=operation)
    except CosmosAccessConditionFailedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.ETAG_CONFLICT)
    except ValidationError as v:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=v.message)


@shared_services_router.delete("/shared-services/{shared_service_id}", response_model=OperationInResponse, name=strings.API_DELETE_SHARED_SERVICE, dependencies=[Depends(get_current_admin_user)])
async def delete_shared_service(response: Response, user=Depends(get_current_admin_user), shared_service=Depends(get_shared_service_by_id_from_path), operations_repo=Depends(get_repository(OperationRepository)), shared_service_repo=Depends(get_repository(SharedServiceRepository)), resource_template_repo=Depends(get_repository(ResourceTemplateRepository))) -> OperationInResponse:
    if shared_service.isEnabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.SHARED_SERVICE_NEEDS_TO_BE_DISABLED_BEFORE_DELETION)

    resource_template = resource_template_repo.get_template_by_name_and_version(shared_service.templateName, shared_service.templateVersion, ResourceType.SharedService)

    operation = await send_uninstall_message(
        resource=shared_service,
        resource_repo=shared_service_repo,
        operations_repo=operations_repo,
        resource_type=ResourceType.SharedService,
        resource_template_repo=resource_template_repo,
        user=user,
        resource_template=resource_template)

    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


@shared_services_router.post("/shared-services/{shared_service_id}/invoke-action", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_INVOKE_ACTION_ON_SHARED_SERVICE, dependencies=[Depends(get_current_admin_user)])
async def invoke_action_on_shared_service(response: Response, action: str, user=Depends(get_current_admin_user), shared_service=Depends(get_shared_service_by_id_from_path), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), operations_repo=Depends(get_repository(OperationRepository)), shared_service_repo=Depends(get_repository(SharedServiceRepository))) -> OperationInResponse:
    operation = await send_custom_action_message(
        resource=shared_service,
        resource_repo=shared_service_repo,
        custom_action=action,
        resource_type=ResourceType.SharedService,
        operations_repo=operations_repo,
        resource_template_repo=resource_template_repo,
        user=user)

    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


# Shared service operations
@shared_services_router.get("/shared-services/{shared_service_id}/operations", response_model=OperationInList, name=strings.API_GET_RESOURCE_OPERATIONS, dependencies=[Depends(get_current_admin_user), Depends(get_shared_service_by_id_from_path)])
async def retrieve_shared_service_operations_by_shared_service_id(shared_service=Depends(get_shared_service_by_id_from_path), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInList:
    return OperationInList(operations=operations_repo.get_operations_by_resource_id(resource_id=shared_service.id))


@shared_services_router.get("/shared-services/{shared_service_id}/operations/{operation_id}", response_model=OperationInResponse, name=strings.API_GET_RESOURCE_OPERATION_BY_ID, dependencies=[Depends(get_current_admin_user), Depends(get_shared_service_by_id_from_path)])
async def retrieve_shared_service_operation_by_shared_service_id_and_operation_id(shared_service=Depends(get_shared_service_by_id_from_path), operation=Depends(get_operation_by_id_from_path)) -> OperationInList:
    return OperationInResponse(operation=operation)
