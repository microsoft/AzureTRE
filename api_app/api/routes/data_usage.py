from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
import logging

from resources import strings
from services.authentication import get_current_workspace_owner_or_tre_user_or_tre_admin
from models.domain.data_usage import MHRAWorkspaceDataUsage
from models.schemas.data_usage import get_workspace_data_usage_responses
from services.data_usage import DataUsageService, data_usage_service_factory

data_usage_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_tre_user_or_tre_admin)])

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
