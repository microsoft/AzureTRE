import logging
import re
from typing import Dict, Optional
from azure.eventgrid import EventGridEvent
from models.domain.events import StatusChangedData, AirlockNotificationData
from event_grid.helpers import publish_event
from core import config
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus


async def send_status_changed_event(airlock_request: AirlockRequest, previous_status: Optional[AirlockRequestStatus]):
    request_id = airlock_request.id
    new_status = airlock_request.status.value
    previous_status = previous_status.value if previous_status else None
    request_type = airlock_request.requestType.value
    short_workspace_id = airlock_request.workspaceId[-4:]

    status_changed_event = EventGridEvent(
        event_type="statusChanged",
        data=StatusChangedData(request_id=request_id, new_status=new_status, previous_status=previous_status, type=request_type, workspace_id=short_workspace_id).__dict__,
        subject=f"{request_id}/statusChanged",
        data_version="2.0"
    )
    logging.info(f"Sending status changed event with request ID {request_id}, new status: {new_status}, previous status: {previous_status}")
    await publish_event(status_changed_event, config.EVENT_GRID_STATUS_CHANGED_TOPIC_ENDPOINT)


async def send_airlock_notification_event(airlock_request: AirlockRequest, emails: Dict):
    request_id = airlock_request.id
    status = airlock_request.status.value
    short_workspace_id = airlock_request.workspaceId[-4:]
    snake_case_emails = {re.sub(r'(?<!^)(?=[A-Z])', '_', role_name).lower(): role_id for role_name, role_id in emails.items()}

    airlock_notification = EventGridEvent(
        event_type="airlockNotification",
        data=AirlockNotificationData(request_id=request_id, event_type="status_changed", event_value=status, emails=snake_case_emails, workspace_id=short_workspace_id).__dict__,
        subject=f"{request_id}/airlockNotification",
        data_version="2.0"
    )
    logging.info(f"Sending airlock notification event with request ID {request_id}, status: {status}")
    await publish_event(airlock_notification, config.EVENT_GRID_AIRLOCK_NOTIFICATION_TOPIC_ENDPOINT)
