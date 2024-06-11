import logging
import httpx, jwt, time
from models.schemas.notify import NotifyUkMessageInput, NotifyUkResponse
from core import config
from fastapi import HTTPException

async def send_message_notify_platform(message_properties: NotifyUkMessageInput) -> NotifyUkResponse:
    # The messages are sent using Notify UK Platform
    iat_date = int(time.time())
    jwt_headers = {"typ":"JWT","alg":"HS256"}
    token_payload = {'iss': config.NOTIFY_UK_ISS_ID,'iat': str(iat_date)}

    jwt_token = jwt.encode(token_payload, config.NOTIFY_UK_SECRET, headers=jwt_headers)

    headers = {'Content-type':'application/json', 'Authorization': 'Bearer ' + jwt_token }

    async with httpx.AsyncClient() as client:
        personalisation_data = { "message": message_properties.message }
        template_data = {
            "email_address": message_properties.recipients,
            "template_id": config.NOTIFY_UK_TEMPLATE_ID,
            "personalisation": personalisation_data
        }

        try:
            response = await client.post(
                config.NOTIFY_UK_URL,
                headers=headers,
                json=template_data
            )

            response.raise_for_status()
            notify_response = response.json()

            return NotifyUkResponse(response=notify_response)

        except httpx.HTTPStatusError:
            logging.info("Error contacting Notify UK API with error code %s", response.status_code)
            raise HTTPException(status_code=response.status_code,
                                detail="Error contacting Notify UK API.")

