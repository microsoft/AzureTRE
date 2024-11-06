import re
import json

from typing import Dict, Optional
from azure.eventgrid import EventGridEvent
from models.domain.events import AirlockNotificationRequestData, AirlockNotificationWorkspaceData, StatusChangedData, AirlockNotificationData
from event_grid.helpers import publish_event
from core import config
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus
from models.domain.workspace import Workspace
from services.logging import logger


async def send_status_changed_event(airlock_request: AirlockRequest, previous_status: Optional[AirlockRequestStatus]):
    request_id = airlock_request.id
    new_status = airlock_request.status.value
    previous_status = previous_status.value if previous_status else None
    request_type = airlock_request.type.value
    short_workspace_id = airlock_request.workspaceId[-4:]

    status_changed_event = EventGridEvent(
        event_type="statusChanged",
        data=StatusChangedData(request_id=request_id, new_status=new_status, previous_status=previous_status, type=request_type, workspace_id=short_workspace_id).__dict__,
        subject=f"{request_id}/statusChanged",
        data_version="2.0"
    )
    logger.info(f"Sending status changed event with request ID {request_id}, new status: {new_status}, previous status: {previous_status}")
    await publish_event(status_changed_event, config.EVENT_GRID_STATUS_CHANGED_TOPIC_ENDPOINT)


async def send_airlock_notification_event(airlock_request: AirlockRequest, workspace: Workspace, role_assignment_details: Dict[str, str]):
    def to_snake_case(string: str):
        return re.sub(r'(?<!^)(?=[A-Z])', '_', string).lower()

    request_id = airlock_request.id
    status = airlock_request.status.value
    recipient_emails_by_role = {to_snake_case(role_name): role_id for role_name, role_id in role_assignment_details.items()}

    data = AirlockNotificationData(
        event_type="status_changed",
        recipient_emails_by_role=recipient_emails_by_role,
        request=AirlockNotificationRequestData(
            id=request_id,
            created_when=airlock_request.createdWhen,
            created_by=airlock_request.createdBy,
            updated_when=airlock_request.updatedWhen,
            updated_by=airlock_request.updatedBy,
            request_type=airlock_request.type,
            files=airlock_request.files,
            status=airlock_request.status.value,
            business_justification=airlock_request.businessJustification),
        workspace=AirlockNotificationWorkspaceData(
            id=workspace.id,
            display_name=workspace.properties["display_name"],
            description=workspace.properties["description"]),
    )

    # For EventGridEvent, data should be a Dict[str, object]
    # Becuase data has nested objects, they all need to be recursively converted to dict
    # To do that, we use a json() method implemented for all objects in AzureTREModel, and convert it back from json
    data_dict = json.loads(data.json())

    airlock_notification = EventGridEvent(
        event_type="airlockNotification",
        data=data_dict,
        subject=f"{request_id}/airlockNotification",
        data_version="4.0"
    )

    logger.info(f"Sending airlock notification event with request ID {request_id}, status: {status}")
    await publish_event(airlock_notification, config.EVENT_GRID_AIRLOCK_NOTIFICATION_TOPIC_ENDPOINT)
