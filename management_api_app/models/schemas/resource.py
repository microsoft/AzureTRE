from pydantic import BaseModel

from models.domain.resource import Resource


class ResourceInResponse(BaseModel):
    resource: Resource
