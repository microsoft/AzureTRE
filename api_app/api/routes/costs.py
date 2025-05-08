from datetime import datetime
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional

from pydantic import UUID4

from models.schemas.costs import get_cost_report_responses, get_workspace_cost_report_responses
from core import config
from api.helpers import get_repository
from db.repositories.shared_services import SharedServiceRepository
from db.repositories.user_resources import UserResourceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.workspaces import WorkspaceRepository
from models.domain.costs import CostReport, GranularityEnum, WorkspaceCostReport
from resources import strings
from services.authentication import get_current_admin_user, get_current_workspace_owner_or_tre_admin
from services.cost_service import CostService, ServiceUnavailable, SubscriptionNotSupported, TooManyRequests, WorkspaceDoesNotExist, cost_service_factory
from services.logging import logger


costs_core_router = APIRouter(dependencies=[Depends(get_current_admin_user)])
costs_workspace_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_tre_admin)])


def validate_report_period(from_date: Optional[datetime], to_date: Optional[datetime]):
    if from_date is None and to_date is None:
        # valid option, month to date report
        return

    if to_date is None or from_date >= to_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=strings.API_GET_COSTS_TO_DATE_NEED_TO_BE_LATER_THEN_FROM_DATE)
    if from_date is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=strings.API_GET_COSTS_FROM_DATE_NEED_TO_BE_BEFORE_TO_DATE)
    if relativedelta(to_date, from_date).years > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.API_GET_COSTS_MAX_TIME_PERIOD)


class CostsQueryParams:
    def __init__(
        self,
        from_date: Optional[datetime] = Query(default=None, description="The start date to pull data from, required if to_date is set, otherwise report will return month to date (iso-8601, UTC)."),
        to_date: Optional[datetime] = Query(default=None, description="The end date to pull data to, required if from_date is set, otherwise report will return month to date (iso-8601, UTC)."),
        granularity: GranularityEnum = Query(default="None", description="The granularity of rows in the query.")
    ):
        self.from_date = from_date
        self.to_date = to_date
        self.granularity = granularity


@costs_core_router.get("/costs", response_model=CostReport, name=strings.API_GET_COSTS,
                       responses=get_cost_report_responses())
async def costs(
        params: CostsQueryParams = Depends(),
        cost_service: CostService = Depends(cost_service_factory),
        workspace_repo=Depends(get_repository(WorkspaceRepository)),
        shared_services_repo=Depends(get_repository(SharedServiceRepository))) -> CostReport:

    validate_report_period(params.from_date, params.to_date)
    try:
        return await cost_service.query_tre_costs(
            config.TRE_ID, params.granularity, params.from_date, params.to_date, workspace_repo, shared_services_repo)
    except SubscriptionNotSupported:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.API_GET_COSTS_SUBSCRIPTION_NOT_SUPPORTED)
    except TooManyRequests as e:
        return JSONResponse(content={
                            "error": {
                                "code": "429",
                                "message": strings.API_GET_COSTS_TOO_MANY_REQUESTS,
                                "retry-after": str(e.retry_after)
                            }}, status_code=429, headers={"Retry-After": str(e.retry_after)})
    except ServiceUnavailable as e:
        return JSONResponse(content={
                            "error": {
                                "code": "503",
                                "message": strings.API_GET_COSTS_SERVICE_UNAVAILABLE,
                                "retry-after": str(e.retry_after)
                            }}, status_code=503, headers={"Retry-After": str(e.retry_after)})
    except Exception:
        logger.exception("Failed to query Azure TRE costs")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=strings.API_GET_COSTS_INTERNAL_SERVER_ERROR)


@costs_workspace_router.get("/workspaces/{workspace_id}/costs", response_model=WorkspaceCostReport,
                            name=strings.API_GET_WORKSPACE_COSTS,
                            dependencies=[Depends(get_current_workspace_owner_or_tre_admin)],
                            responses=get_workspace_cost_report_responses())
async def workspace_costs(workspace_id: UUID4, params: CostsQueryParams = Depends(),
                          cost_service: CostService = Depends(cost_service_factory),
                          workspace_repo=Depends(get_repository(WorkspaceRepository)),
                          workspace_services_repo=Depends(get_repository(WorkspaceServiceRepository)),
                          user_resource_repo=Depends(get_repository(UserResourceRepository))) -> WorkspaceCostReport:

    validate_report_period(params.from_date, params.to_date)
    try:
        return await cost_service.query_tre_workspace_costs(
            str(workspace_id), params.granularity, params.from_date, params.to_date,
            workspace_repo, workspace_services_repo, user_resource_repo)
    except WorkspaceDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_DOES_NOT_EXIST)
    except SubscriptionNotSupported:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.API_GET_COSTS_SUBSCRIPTION_NOT_SUPPORTED)
    except TooManyRequests as e:
        return JSONResponse(content={
                            "error": {
                                "code": "429",
                                "message": strings.API_GET_COSTS_TOO_MANY_REQUESTS,
                                "retry-after": str(e.retry_after)
                            }}, status_code=429, headers={"Retry-After": str(e.retry_after)})
    except ServiceUnavailable as e:
        return JSONResponse(content={
                            "error": {
                                "code": "503",
                                "message": strings.API_GET_COSTS_SERVICE_UNAVAILABLE,
                                "retry-after": str(e.retry_after)
                            }}, status_code=503, headers={"Retry-After": str(e.retry_after)})
    except Exception:
        logger.exception("Failed to query Azure TRE costs")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=strings.API_GET_COSTS_INTERNAL_SERVER_ERROR)
