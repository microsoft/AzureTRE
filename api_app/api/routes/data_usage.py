from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from azure.core.exceptions import HttpResponseError
import logging

from resources import strings
from services.authentication import get_current_workspace_owner_or_tre_user_or_tre_admin
from models.domain.data_usage import MHRAWorkspaceDataUsage, MHRAStorageAccountLimits, MHRAStorageAccountLimitsItem, StorageAccountLimitsInput
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
