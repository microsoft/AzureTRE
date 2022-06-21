from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import pytz
from fastapi import APIRouter, Depends, Query, HTTPException, status

from api.dependencies.database import get_repository
from core import config
from db.repositories.shared_services import SharedServiceRepository
from db.repositories.user_resources import UserResourceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.workspaces import WorkspaceRepository
from models.domain.costs import CostReport, GranularityEnum, WorkspaceCostReport, generate_cost_report_stub, \
    generate_workspace_cost_report_stub
from resources import strings
from services.authentication import get_current_admin_user, get_current_workspace_owner_or_tre_admin
from services.cost_service import CostService

costs_core_router = APIRouter(dependencies=[Depends(get_current_admin_user)])
costs_workspace_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_tre_admin)])


def get_first_day_of_month():
    return date_to_datetime(date.today().replace(day=1))


def get_eod_datetime():
    return datetime.now().replace(hour=23, minute=59, second=59)


def date_to_datetime(date_to_covert: date):
    converted_datetime = datetime.combine(date_to_covert, datetime.min.time())
    converted_datetime.replace(tzinfo=pytz.UTC)
    return converted_datetime


def check_time_period(from_date: datetime, to_date: datetime):
    if relativedelta(to_date, from_date).years > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.API_GET_COSTS_MAX_TIME_PERIOD)
    elif from_date >= to_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.API_GET_COSTS_TO_DATE_NEED_TO_BE_LATER_THEN_FROM_DATE)


class CostsQueryParams:
    def __init__(
        self,
        call_service: bool = Query(default=False, description="A feature flag which will get removed as soon as the feature is implemented"),
        from_date: datetime = Query(default=get_first_day_of_month(), description="The start date to pull data from, default value first day of month (iso-8601, UTC)."),
        to_date: datetime = Query(default=get_eod_datetime(), description="The end date to pull data to, default end of day (iso-8601, UTC)."),
        granularity: GranularityEnum = Query(default="None", description="The granularity of rows in the query.")
    ):
        self.call_service = call_service
        self.from_date = from_date
        self.to_date = to_date
        self.granularity = granularity


@costs_core_router.get("/costs", response_model=CostReport, name=strings.API_GET_COSTS)
async def costs(
        params: CostsQueryParams = Depends(),
        workspace_repo=Depends(get_repository(WorkspaceRepository)),
        shared_services_repo=Depends(get_repository(SharedServiceRepository))) -> CostReport:

    # todo - remove this flag and stubs when the feature is done
    if params.call_service:
        check_time_period(params.from_date, params.to_date)
        cost_service = CostService()
        return cost_service.query_tre_costs(
            config.TRE_ID, params.granularity, params.from_date, params.to_date, workspace_repo, shared_services_repo)
    else:
        return generate_cost_report_stub(params.granularity)


@costs_workspace_router.get("/workspaces/{workspace_id}/costs", response_model=WorkspaceCostReport, name=strings.API_GET_WORKSPACE_COSTS, dependencies=[Depends(get_current_workspace_owner_or_tre_admin)])
async def workspace_costs(
        workspace_id, params: CostsQueryParams = Depends(),
        workspace_repo=Depends(get_repository(WorkspaceRepository)),
        workspace_services_repo=Depends(get_repository(WorkspaceServiceRepository)),
        user_resource_repo=Depends(get_repository(UserResourceRepository))) -> WorkspaceCostReport:

    # todo - remove this flag and stubs when the feature is done
    if params.call_service:
        check_time_period(params.from_date, params.to_date)
        cost_service = CostService()
        cost_service.query_tre_workspace_costs(
            workspace_id, params.granularity, params.from_date, params.to_date,
            workspace_repo, workspace_services_repo, user_resource_repo)

    return generate_workspace_cost_report_stub("Workspace 1", params.granularity)


