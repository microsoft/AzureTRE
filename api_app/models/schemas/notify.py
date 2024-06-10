from pydantic import BaseModel, Field

class NotifyUkMessageInput(BaseModel):
    recipients: str = Field("Recipient list to be sent to Notify UK Platform", title="Recipient list to be sent to Notify UK Platform")
    message: str = Field("Content of the message to be sent to Notify UK", title="Content of the message to be sent to Notify UK")

    class Config:
        schema_extra = {
            "example": {
                "recipients": "email@domain.com",
                "message": "This is the content of the message."
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
