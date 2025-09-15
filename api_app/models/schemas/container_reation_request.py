from pydantic import BaseModel
from typing import List, Optional

class ContainerCreateRequest(BaseModel):
    workspaceId: Optional[str] = None
    protocolId: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "workspaceId": "ed299",
                "protocolId": "25-123456"
            }
        }
