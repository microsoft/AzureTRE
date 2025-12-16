
from datetime import datetime
import logging
from uuid import uuid4
from services.cost_service import CostService, cost_service_factory
from db.repositories.user_resources import UserResourceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.workspaces import WorkspaceRepository
from api.dependencies.database import get_db_client
from models.domain.costs import GranularityEnum, WorkspaceCostReport
from core import config, credentials
from resources import constants
from azure.data.tables import TableServiceClient, UpdateMode
from fastapi import Depends

def to_iso8601(dt, end_of_day=False):

    if dt is None:
        return None
    if end_of_day:
        return dt.replace(hour=23, minute=59, second=59).isoformat() + 'Z'
    return dt.isoformat() + 'Z'

async def update_workspace_costs(
    app
):
    cost_service = cost_service_factory()
    db_client = await get_db_client(app)
    user_resource_repo = await UserResourceRepository.create(db_client)
    workspace_repo = await WorkspaceRepository.create(db_client)
    workspace_services_repo = await WorkspaceServiceRepository.create(db_client)

    granularity = GranularityEnum.daily
    to_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    from_date = to_date.replace(day=1, hour=0, minute=0, second=0)

    account_name = constants.STORAGE_ACCOUNT_NAME_CORE_RESOURCE_GROUP.format(config.TRE_ID)
    account_endpoint = f"https://{account_name}.table.core.windows.net"

    client = TableServiceClient(
        endpoint=account_endpoint,
        credential=credentials.get_credential(),
        headers={"ClientType": config.CLIENT_TYPE_CUSTOM_HEADER}
    )

    workspaces = await workspace_repo.get_active_workspaces()
    table_client = client.get_table_client(table_name="workspacecosts")

    for workspace in workspaces:
        report: WorkspaceCostReport = await cost_service.query_tre_workspace_costs(
            workspace_id=workspace.id,
            granularity=granularity,
            from_date=from_date,
            to_date=to_date,
            workspace_repo=workspace_repo,
            workspace_services_repo=workspace_services_repo,
            user_resource_repo=user_resource_repo
        )

        report_json = report.json()
        # Azure Table Storage property size limit is 64KB (65536 bytes)

        if len(report_json.encode('utf-8')) > 64000:
            logging.error(f"WorkspaceCosts property too large to store in Table Storage for workspace {workspace.id} (size: {len(report_json.encode('utf-8'))} bytes)")
            return

        new_entity = {
            "PartitionKey": str(uuid4()),
            "RowKey": str(uuid4()),
            "Timestamp": datetime.utcnow().isoformat() + 'Z',
            "FromDate": to_iso8601(from_date),
            "ToDate": to_iso8601(to_date, end_of_day=True),
            "WorkspaceCosts": report_json,
            "WorkspaceId": workspace.id
        }

        try:
            table_client.upsert_entity(entity=new_entity, mode=UpdateMode.MERGE)
        except Exception as e:
            logging.error(f"Failed to upsert entity for workspace {workspace.id}: {e}")
