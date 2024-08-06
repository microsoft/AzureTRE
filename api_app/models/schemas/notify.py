from pydantic import BaseModel, Field

class NotifyUkMessageInput(BaseModel):
    recipients: str = Field("Recipient list to be sent to Notify UK Platform", title="Recipient list to be sent to Notify UK Platform")
    secondary_recipients: str = Field("Secondary recipient list to be sent to Notify UK Platform", title="Secondary recipient list to be sent to Notify UK Platform")
    name: str = Field("Name of the Researcher who sent the support request", title="Name of the Researcher who sent the support request")
    email: str = Field("Email address of the Researcher who sent the support request", title="Email address of the Researcher who sent the support request")
    subject: str = Field("Email subject of the message sent to support team", title="Email subject of the message sent to support team")
    workspace: str = Field("Workspace ID of the workspace where the problem happened", title="Workspace ID of the workspace where the problem happened")
    issue_type: str = Field("Issue type related to the problem reported", title="Issue type related to the problem reported")
    error_message: str = Field("Error message received by the Researcher", title="Error message received by the Researcher")
    issue_description: str = Field("Issue description given by the Researcher", title="Issue description given by the Researcher")

    class Config:
        schema_extra = {
            "example": {
                "recipients": "email@domain.com",
                "secondary_recipients": "email1@domain.com, email2@domain.com, email3@domain.com",
                "name": "John Smith",
                "email": "john.smith@email.com",
                "subject": "Email subject",
                "workspace": "b0aec2c5-658a-4a74-b48e-e0ee6cd1d8a4",
                "issue_type": "Issue type 1",
                "error_message": "Error message received by user",
                "issue_description": "I have an error"
            }
        }

class NotifyUkResponse(BaseModel):
    response: dict = Field({}, title="HTTP response sent by Notify UK Platform", description="HTTP response sent by Notify UK Platform")

    class Config:
        schema_extra = {
            "response": {
                "content": {
                    "body": "MESSAGE_BODY",
                    "from_email": "SENDER_EMAIL",
                    "one_click_unsubscribe_url": "null",
                    "subject": "SUBJECT_TEXT"
                },
                "id": "893fbf31-b480-4738-970f-72589679471b",
                "reference": "null",
                "scheduled_for": "null",
                "template": {
                    "id": "8849fbcb-2e7a-4c51-98ab-0e506a3ced30",
                    "uri": "https://api.notifications.service.gov.uk/services/4f09ada1-6aa6-4352-9eb5-41a1ab45c111/templates/8849fbcb-2e7a-4c51-98ab-0e506a3ced30",
                    "version": 2
                },
                "uri": "https://api.notifications.service.gov.uk/v2/notifications/893fbf31-b480-4738-970f-72589679471b"
            }
        }
