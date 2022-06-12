import logging
from azure.eventgrid import EventGridEvent
from azure.eventgrid.aio import EventGridPublisherClient
from azure.core.credentials import AzureKeyCredential
from models.domain.airlock_request import AirlockRequest
from core import config


async def _publish_event(event: EventGridEvent, topic_key: str, topic_endpoint: str):
    credential = AzureKeyCredential(topic_key)
    client = EventGridPublisherClient(topic_endpoint, credential)

    await client.send([event])


async def send_status_changed_event(airlock_request: AirlockRequest):
    request_id = airlock_request.id
    status = airlock_request.status
    request_type = airlock_request.requestType
    workspace_id = airlock_request.workspaceId

    status_changed_event = EventGridEvent(
        event_type="statusChanged",
        data={
            "request_id": request_id,
            "status": status,
            "type": request_type,
            "workspace_id": workspace_id
        },
        subject=f"{request_id}/statusChanged",
        data_version="2.0"
    )
    logging.info(f"Sending status changed event with request ID {request_id}, status: {status}")
    await _publish_event(status_changed_event, config.EVENT_GRID_ACCESS_KEY, config.EVENT_GRID_TOPIC_ENDPOINT)
