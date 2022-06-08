from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query

from resources import strings
from api.dependencies.database import get_repository
from api.dependencies.workspaces import get_workspace_by_id_from_path
from services.authentication import get_current_admin_user, get_current_workspace_owner_user
from db.repositories.workspaces import WorkspaceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.shared_services import SharedServiceRepository
from models.domain.costs import CostReport, GranularityEnum, WorkspaceCostReport, generate_cost_report_stub, generate_workspace_cost_report_stub


costs_core_router = APIRouter(dependencies=[Depends(get_current_admin_user)])
costs_workspace_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_user)])


class CostsQueryParams:
    def __init__(
        self,
        from_date: date = Query(default=(date.today().replace(day=1)), description="The start date to pull data from, default value first day of month (iso-8601, UTC)."),
        to_date: date = Query(default=(date.today() + timedelta(days=1)), description="The end date to pull data to, default value tomorrow (iso-8601, UTC)."),
        granularity: GranularityEnum = Query(default="None", description="The granularity of rows in the query.")
    ):
        self.from_date = from_date
        self.to_date = to_date
        self.granularity = granularity


@costs_core_router.get("/costs", response_model=CostReport, name=strings.API_GET_COSTS)
async def costs(params: CostsQueryParams = Depends(), workspace_repo=Depends(get_repository(WorkspaceRepository)), shared_services_repo=Depends(get_repository(SharedServiceRepository))) -> CostReport:
    return generate_cost_report_stub(params.granularity)


@costs_workspace_router.get("/workspaces/{workspace_id}/costs", response_model=WorkspaceCostReport, name=strings.API_GET_WORKSPACE_COSTS, dependencies=[Depends(get_current_workspace_owner_user)])
async def workspace_costs(params: CostsQueryParams = Depends(), workspace=Depends(get_workspace_by_id_from_path), workspace_services_repo=Depends(get_repository(WorkspaceServiceRepository))) -> WorkspaceCostReport:
    return generate_workspace_cost_report_stub("Workspace 1", params.granularity)
