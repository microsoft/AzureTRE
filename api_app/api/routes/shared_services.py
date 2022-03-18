import logging

from fastapi import APIRouter, Depends, HTTPException, Header, status, Response
from jsonschema.exceptions import ValidationError

from db.repositories.operations import OperationRepository
from api.dependencies.database import get_repository
from api.dependencies.shared_services import get_shared_service_by_id_from_path, get_operation_by_id_from_path
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.shared_services import SharedServiceRepository
from models.domain.resource import ResourceType
from models.schemas.operation import OperationInList, OperationInResponse
from models.schemas.shared_service import SharedServiceInCreate, SharedServicesInList, SharedServiceInResponse
from models.schemas.resource import ResourcePatch
from resources import strings
from .workspaces import save_and_deploy_resource, check_for_etag, construct_location_header
from azure.cosmos.exceptions import CosmosAccessConditionFailedError
from .resource_helpers import send_custom_action_message, send_uninstall_message, send_resource_request_message
from services.authentication import get_current_admin_user, get_current_tre_user_or_tre_admin
from models.domain.request_action import RequestAction


shared_services_router = APIRouter(dependencies=[Depends(get_current_tre_user_or_tre_admin)])


@shared_services_router.get("/shared-services", response_model=SharedServicesInList, name=strings.API_GET_ALL_SHARED_SERVICES, dependencies=[Depends(get_current_tre_user_or_tre_admin)])
async def retrieve_shared_services(shared_services_repo=Depends(get_repository(SharedServiceRepository))) -> SharedServicesInList:
    shared_services = shared_services_repo.get_active_shared_services()
    return SharedServicesInList(sharedServices=shared_services)


@shared_services_router.get("/shared-services/{shared_service_id}", response_model=SharedServiceInResponse, name=strings.API_GET_SHARED_SERVICE_BY_ID, dependencies=[Depends(get_current_admin_user), Depends(get_shared_service_by_id_from_path)])
async def retrieve_shared_service_by_id(shared_service=Depends(get_shared_service_by_id_from_path)) -> SharedServiceInResponse:
    return SharedServiceInResponse(sharedService=shared_service)


@shared_services_router.post("/shared-services", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_CREATE_SHARED_SERVICE, dependencies=[Depends(get_current_admin_user)])
async def create_shared_service(response: Response, shared_service_input: SharedServiceInCreate, shared_services_repo=Depends(get_repository(SharedServiceRepository)), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInResponse:
    try:
        shared_service = shared_services_repo.create_shared_service_item(shared_service_input)
    except (ValidationError, ValueError) as e:
        logging.error(f"Failed create shared service model instance: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    operation = await save_and_deploy_resource(shared_service, shared_services_repo, operations_repo)
    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


@shared_services_router.patch("/shared-services/{shared_service_id}", response_model=SharedServiceInResponse, name=strings.API_UPDATE_SHARED_SERVICE, dependencies=[Depends(get_current_admin_user), Depends(get_shared_service_by_id_from_path)])
async def patch_shared_service(shared_service_patch: ResourcePatch, response: Response, shared_service_repo=Depends(get_repository(SharedServiceRepository)), shared_service=Depends(get_shared_service_by_id_from_path), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), operations_repo=Depends(get_repository(OperationRepository)), etag: str = Header(None)) -> SharedServiceInResponse:
    check_for_etag(etag)
    try:
        patched_shared_service = shared_service_repo.patch_shared_service(shared_service, shared_service_patch, etag, resource_template_repo)
        operation = await send_resource_request_message(patched_shared_service, operations_repo, RequestAction.Upgrade)
        response.headers["Location"] = construct_location_header(operation)
        return SharedServiceInResponse(sharedService=patched_shared_service)
    except CosmosAccessConditionFailedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.ETAG_CONFLICT)
    except ValidationError as v:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=v.message)


@shared_services_router.delete("/shared-services/{shared_service_id}", response_model=OperationInResponse, name=strings.API_DELETE_SHARED_SERVICE, dependencies=[Depends(get_current_admin_user)])
async def delete_shared_service(response: Response, shared_service=Depends(get_shared_service_by_id_from_path), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInResponse:
    if shared_service.isEnabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.SHARED_SERVICE_NEEDS_TO_BE_DISABLED_BEFORE_DELETION)

    operation = await send_uninstall_message(shared_service, operations_repo, ResourceType.SharedService)
    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


@shared_services_router.post("/shared-services/{shared_service_id}/invoke-action", status_code=status.HTTP_202_ACCEPTED, response_model=OperationInResponse, name=strings.API_INVOKE_ACTION_ON_SHARED_SERVICE, dependencies=[Depends(get_current_admin_user)])
async def invoke_action_on_shared_service(response: Response, action: str, shared_service=Depends(get_shared_service_by_id_from_path), resource_template_repo=Depends(get_repository(ResourceTemplateRepository)), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInResponse:
    operation = await send_custom_action_message(shared_service, action, ResourceType.SharedService, operations_repo, resource_template_repo)
    response.headers["Location"] = construct_location_header(operation)

    return OperationInResponse(operation=operation)


# Shared service operations
@shared_services_router.get("/shared-services/{shared_service_id}/operations", response_model=OperationInList, name=strings.API_GET_RESOURCE_OPERATIONS, dependencies=[Depends(get_current_admin_user), Depends(get_shared_service_by_id_from_path)])
async def retrieve_shared_service_operations_by_shared_service_id(shared_service=Depends(get_shared_service_by_id_from_path), operations_repo=Depends(get_repository(OperationRepository))) -> OperationInList:
    return OperationInList(operations=operations_repo.get_operations_by_resource_id(resource_id=shared_service.id))


@shared_services_router.get("/shared-services/{shared_service_id}/operations/{operation_id}", response_model=OperationInResponse, name=strings.API_GET_RESOURCE_OPERATION_BY_ID, dependencies=[Depends(get_current_admin_user), Depends(get_shared_service_by_id_from_path)])
async def retrieve_shared_service_operation_by_shared_service_id_and_operation_id(shared_service=Depends(get_shared_service_by_id_from_path), operation=Depends(get_operation_by_id_from_path)) -> OperationInList:
    return OperationInResponse(operation=operation)
