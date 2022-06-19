from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException, status

from resources import strings
from api.dependencies.database import get_repository
from api.dependencies.workspaces import get_workspace_by_id_from_path
from services.authentication import get_current_admin_user, get_current_workspace_owner_or_tre_admin
from db.repositories.workspaces import WorkspaceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.shared_services import SharedServiceRepository
from db.repositories.user_resources import UserResourceRepository
from models.domain.costs import CostReport, GranularityEnum, WorkspaceCostReport, generate_cost_report_stub, generate_workspace_cost_report_stub
from services.cost_service import CostService
from core import config

costs_core_router = APIRouter(dependencies=[Depends(get_current_admin_user)])
costs_workspace_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_tre_admin)])


class CostsQueryParams:
    def __init__(
        self,
        call_service: bool = Query(default=False),
        from_date: date = Query(default=(date.today().replace(day=1)), description="The start date to pull data from, default value first day of month (iso-8601, UTC)."),
        to_date: date = Query(default=(date.today() + timedelta(days=1)), description="The end date to pull data to, default value tomorrow (iso-8601, UTC)."),
        granularity: GranularityEnum = Query(default="None", description="The granularity of rows in the query.")
    ):
        self.call_service = call_service
        self.from_date = from_date
        self.to_date = to_date
        self.granularity = granularity


def check_time_period(from_date: date, to_date: date):
    if (to_date - from_date).days > 365:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.API_GET_COSTS_INVALID_TIME_PERIOD)


@costs_core_router.get("/costs", response_model=CostReport, name=strings.API_GET_COSTS)
async def costs(
        params: CostsQueryParams = Depends(),
        workspace_repo=Depends(get_repository(WorkspaceRepository)),
        shared_services_repo=Depends(get_repository(SharedServiceRepository))) -> CostReport:

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

    if params.call_service:
        check_time_period(params.from_date, params.to_date)
        cost_service = CostService()
        cost_service.query_tre_workspace_costs(
            workspace_id, params.granularity, params.from_date, params.to_date,
            workspace_repo, workspace_services_repo, user_resource_repo)

    return generate_workspace_cost_report_stub("Workspace 1", params.granularity)
