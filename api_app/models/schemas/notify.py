from pydantic import BaseModel, Field

class NotifyUkMessageInput(BaseModel):
    recipients: str = Field("Recipient list to be sent to Notify UK Platform", title="Recipient list to be sent to Notify UK Platform")
    message: str = Field("Content of the message to be sent to Notify UK", title="Content of the message to be sent to Notify UK")

    class Config:
        schema_extra = {
            "example": {
                "recipients": "email@domain.com",
                "name": "John Smith",
                "email": "john.smith@email.com",
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
            "example": {
                "response": "HTTP/1.1 201 CREATED"
            }
        }
