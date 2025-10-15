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

class EntraGroupRequest(BaseModel):
    workspaceId: Optional[str] = None
    protocolId: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "workspaceId": "ed299",
                "protocolId": "25-123456"
            }
        }

class RoleAssignmentRequest(BaseModel):
    workspaceId: Optional[str] = None
    groupId: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "workspaceId": "ed299",
                "groupId": "123456"
            }
        }


class EntraGroup(BaseModel):
    id: str
    display_name: str
    mail_nickname: str
    security_enabled: bool
