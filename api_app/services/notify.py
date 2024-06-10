import logging
import httpx, jwt, time
from models.schemas.notify import NotifyUkMessageInput, NotifyUkResponse

from fastapi import HTTPException

async def send_message_notify_platform(message_properties: NotifyUkMessageInput) -> NotifyUkResponse:
# The messages are sent using Notify UK Platform
    iss_id = "4f09ada1-6aa6-4352-9eb5-41a1ab45c111"
    iat_date = int(time.time())

    notify_secret = 'b46b243f-3de5-4478-8e33-abe989b690ce'

    jwt_headers = {"typ":"JWT","alg":"HS256"}
    token_payload = {'iss': iss_id,'iat': str(iat_date)}
    jwt_token = jwt.encode(token_payload, notify_secret, headers=jwt_headers)

    headers = {'Content-type':'application/json', 'Authorization': 'Bearer ' + jwt_token }

    NOTIFY_RECIPIENT = message_properties.recipients
    NOTIFY_UK_URL = "https://api.notifications.service.gov.uk/v2/notifications/email"

    NOTIFY_TEMPLATE_ID = "670432d9-02fd-48f9-9972-7d7e2a037ae4"
    async with httpx.AsyncClient() as client:
        personalisation_data = { "message": message_properties.message }
        template_data = {
            "email_address": NOTIFY_RECIPIENT,
            "template_id": NOTIFY_TEMPLATE_ID,
            "personalisation": personalisation_data
        }

        try:
            response = await client.post(
                NOTIFY_UK_URL,
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

