import logging
import httpx, jwt, re, time
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

    # Remove empty chars from the input, split the secondary recipients string and create the final list.
    replaced_secondary_recipients = message_properties.secondary_recipients.replace(" ", "")
    secondary_recipients_list = replaced_secondary_recipients.split(",")

    # This list will contain at least the Support Team email address.
    validated_secondary_recipients_list = []
    validated_secondary_recipients_list.append(message_properties.recipients)

    # Remove malformed email addresses.
    # This regex will validate email addresses sent to the API.
    email_regex_validation = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    for item in secondary_recipients_list:
        if(re.fullmatch(email_regex_validation, item)):
            validated_secondary_recipients_list.append(item)

    email_subject_tag = ""
    if config.NOTIFY_UK_EMAIL_SUBJECT_TAG != "":
        email_subject_tag = f"{config.NOTIFY_UK_EMAIL_SUBJECT_TAG}: "

    async with httpx.AsyncClient() as client:
        personalisation_data = {
            "name": message_properties.name,
            "email": message_properties.email,
            "subject": f"{email_subject_tag}{message_properties.subject}",
            "workspace": message_properties.workspace,
            "issue_type": message_properties.issue_type,
            "error_message": message_properties.error_message,
            "issue_description": message_properties.issue_description
        }

        try:
            for recipient in validated_secondary_recipients_list:
                template_data = {
                    "email_address": recipient,
                    "template_id": config.NOTIFY_UK_TEMPLATE_ID,
                    "personalisation": personalisation_data
                }

                response = await client.post(
                    config.NOTIFY_UK_URL,
                    headers=headers,
                    json=template_data
                )

                response.raise_for_status()

        except httpx.HTTPStatusError:
            logging.info("Error contacting Notify UK API with error code %s", response.status_code)
            raise HTTPException(status_code=response.status_code,
                                detail="Error contacting Notify UK API.")

        notify_response = response.json()
        return NotifyUkResponse(response=notify_response)


