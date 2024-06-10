from fastapi import APIRouter, HTTPException, status as status_code
from resources import strings
from services.notify import send_message_notify_platform
from models.schemas.notify import NotifyUkResponse, NotifyUkMessageInput

import logging

send_message_support_team = APIRouter()

@send_message_support_team.post("/support",
                               name=strings.API_MESSAGE_SUPPORT_TEAM,
                               response_model=NotifyUkResponse,
                               status_code=status_code.HTTP_201_CREATED)
async def send_message_notify_platform_route(message_properties: NotifyUkMessageInput) -> NotifyUkResponse:
    try:
        response = await send_message_notify_platform(message_properties)
    except Exception as e:
        logging.info("Error contacting Notify UK API. With error message: %s", str(e))
        raise HTTPException(status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return response
