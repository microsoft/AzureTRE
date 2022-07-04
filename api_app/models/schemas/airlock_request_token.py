from pydantic import BaseModel


def get_sample_airlock_request_container_url(container_url: str) -> dict:
    return {
        "containerUrl": container_url
    }


class AirlockRequestTokenInResponse(BaseModel):
    containerUrl: str

    class Config:
        schema_extra = {
            "example": {
                "container_url": get_sample_airlock_request_container_url("container_url")
            }
        }
