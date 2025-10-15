from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from azure.core.exceptions import HttpResponseError
import logging

from api.dependencies.database import get_repository
from models.schemas.container_reation_request import ContainerCreateRequest, EntraGroup, EntraGroupRequest, RoleAssignmentRequest
from db.repositories.workspaces import WorkspaceRepository
from resources import strings
from services.authentication import get_current_workspace_owner_or_tre_user_or_tre_admin
from models.domain.data_usage import MHRAProtocolList, MHRAWorkspaceDataUsage, MHRAStorageAccountLimits, MHRAStorageAccountLimitsItem, StorageAccountLimitsInput, WorkspaceDataUsage
from models.schemas.data_usage import get_workspace_data_usage_responses, get_storage_account_limits_responses, get_storage_info_responses
from models.schemas.storage_info_request import StorageInfoRequest
from services.data_usage import DataUsageService, data_usage_service_factory

data_usage_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_tre_user_or_tre_admin)])
get_storage_account_limits = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_tre_user_or_tre_admin)])
set_storage_account_limits = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_tre_user_or_tre_admin)])

@data_usage_router.get("/data_usage", response_model=MHRAWorkspaceDataUsage,
                       status_code=status.HTTP_200_OK,
                       name=strings.API_GET_WORKSPACE_DATA_USAGE_CLIENTS,
                       dependencies=[Depends(get_current_workspace_owner_or_tre_user_or_tre_admin)],
                       responses=get_workspace_data_usage_responses())
async def get_workspace_data_usage_method(data_usage_service: DataUsageService = Depends(data_usage_service_factory)) -> MHRAWorkspaceDataUsage:
    try:
        return await data_usage_service.get_workspace_data_usage()
    except:
        logging.exception("Failed to retrieve Workspace data usage.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=strings.API_GET_WORKSPACE_DATA_USAGE_INTERNAL_SERVER_ERROR)

@get_storage_account_limits.get("/storage_account_limit", response_model=MHRAStorageAccountLimits,
                       status_code=status.HTTP_200_OK,
                       name=strings.API_GET_WORKSPACE_DATA_USAGE_CLIENTS,
                       dependencies=[Depends(get_current_workspace_owner_or_tre_user_or_tre_admin)],
                       responses=get_storage_account_limits_responses())
async def get_storage_account_limits_method(data_usage_service: DataUsageService = Depends(data_usage_service_factory)) -> MHRAStorageAccountLimits:
    try:
        return await data_usage_service.get_storage_account_limits()
    except:
        logging.exception("Failed to retrieve Storage account data limits.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=strings.API_GET_WORKSPACE_DATA_USAGE_INTERNAL_SERVER_ERROR)

@set_storage_account_limits.post("/storage_account_limit", response_model=MHRAStorageAccountLimitsItem,
                       status_code=status.HTTP_200_OK,
                       name=strings.API_CREATE_WORKSPACE_DATA_USAGE_CLIENTS,
                       dependencies=[Depends(get_current_workspace_owner_or_tre_user_or_tre_admin)],
                       responses=get_storage_account_limits_responses())
async def set_storage_account_limits_method(storage_account_lits_properties: StorageAccountLimitsInput = Depends(),
                                            data_usage_service: DataUsageService = Depends(data_usage_service_factory)) -> MHRAStorageAccountLimitsItem:
    try:
        return await data_usage_service.set_storage_account_limits(storage_account_lits_properties)
    except HTTPException as ex:
            logging.info(f"\t{ex.detail}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ex.detail)
    except:
        logging.exception(f"{strings.API_GET_WORKSPACE_DATA_USAGE_INTERNAL_SERVER_ERROR}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=strings.API_GET_WORKSPACE_DATA_USAGE_INTERNAL_SERVER_ERROR)



@data_usage_router.post("/storage_info", response_model=MHRAWorkspaceDataUsage,
                       status_code=status.HTTP_200_OK,
                       name=strings.API_GET_WORKSPACE_STORAGE_INFO,
                       dependencies=[Depends(get_current_workspace_owner_or_tre_user_or_tre_admin)],
                       responses=get_storage_info_responses())
async def get_workspace_storage(storage_info_request :StorageInfoRequest = None,
                                     data_usage_service: DataUsageService = Depends(data_usage_service_factory)) -> MHRAWorkspaceDataUsage:
    try:
        if storage_info_request is not None and storage_info_request.workspaceIds:
            return await data_usage_service.get_workspace_storage_info(storage_info_request)
        else :
            return await data_usage_service.get_workspace_data_usage()
    except:
        logging.exception("Failed to retrieve Workspace data usage.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=strings.API_GET_WORKSPACE_DATA_USAGE_INTERNAL_SERVER_ERROR)

@get_storage_account_limits.get("/protocol_items/{workspaceId}", response_model=MHRAProtocolList,
                       status_code=status.HTTP_200_OK,
                       name=strings.API_GET_PERSTUDY_ITEMS,
                       dependencies=[Depends(get_current_workspace_owner_or_tre_user_or_tre_admin)])
async def get_perstudy_items_method(workspaceId: str, data_usage_service: DataUsageService = Depends(data_usage_service_factory)) -> MHRAProtocolList:
    try:
        return await data_usage_service.get_perstudy_items(workspaceId)
    except Exception as exc:
        logging.exception("Failed to retrieve Protocol item: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=strings.API_GET_WORKSPACE_DATA_USAGE_INTERNAL_SERVER_ERROR)

@get_storage_account_limits.get("/data_usage/{workspaceId}", response_model=WorkspaceDataUsage,
                       status_code=status.HTTP_200_OK,
                       name=strings.API_GET_WORKSPACE_DATA_USAGE_CLIENTS,
                       dependencies=[Depends(get_current_workspace_owner_or_tre_user_or_tre_admin)])
async def get_data_usage_for_workspace(workspaceId: str,data_usage_service: DataUsageService = Depends(data_usage_service_factory)) -> WorkspaceDataUsage:
    try:
        return await data_usage_service.get_data_usage_for_workspace(workspaceId)
    except:
        logging.exception("Failed to retrieve Workspace data usage.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=strings.API_GET_WORKSPACE_DATA_USAGE_INTERNAL_SERVER_ERROR)

@data_usage_router.post("/container-creation",
                       status_code=status.HTTP_201_CREATED,
                       name=strings.API_CREATE_CONTAINER_AND_FOLDER,
                       dependencies=[Depends(get_current_workspace_owner_or_tre_user_or_tre_admin)])
async def create_container(conatiner_create_request: ContainerCreateRequest = None,
                           data_usage_service: DataUsageService = Depends(data_usage_service_factory),
                           workspace_repo: WorkspaceRepository = Depends(get_repository(WorkspaceRepository))) -> dict:
    try:
        await data_usage_service.create_container(conatiner_create_request, workspace_repo)
        return {"message": "Container created successfully"}
    except Exception as e:
        logging.exception("Failed to create container.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create container")

@data_usage_router.post("/roles-group-create",
                       status_code=status.HTTP_201_CREATED,
                       name=strings.API_CREATE_USER_RESOURCE_GROUP,
                       dependencies=[Depends(get_current_workspace_owner_or_tre_user_or_tre_admin)])
async def create_roles_group(group_request: EntraGroupRequest = None,
                           data_usage_service: DataUsageService = Depends(data_usage_service_factory)) -> EntraGroup:
    try:

        return await data_usage_service.create_group(group_request)
    except Exception as e:
        logging.exception("Failed to create Roles group.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create Roles group.")

@data_usage_router.post("/assign-roles-to-group",
                       status_code=status.HTTP_201_CREATED,
                       name=strings.API_ASSIGN_ROLE_TO_GROUP,
                       dependencies=[Depends(get_current_workspace_owner_or_tre_user_or_tre_admin)])
async def assign_roles_to_group(role_assignment_request: RoleAssignmentRequest = None,
                           data_usage_service: DataUsageService = Depends(data_usage_service_factory)) -> dict:
    try:

        await data_usage_service.assign_role_to_group(role_assignment_request)
        return {"message": "Roles assigned to group successfully"}
    except Exception as e:
        logging.exception("Failed to role assigned to group.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create Roles group.")
