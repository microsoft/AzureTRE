from pydantic import ConfigDict, BaseModel


def get_sample_airlock_request_container_url(container_url: str) -> dict:
    return {
        "containerUrl": container_url
    }


class AirlockRequestTokenInResponse(BaseModel):
    containerUrl: str
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "container_url": get_sample_airlock_request_container_url("container_url")
        }
    })
