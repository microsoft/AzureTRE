from pydantic import BaseModel
from typing import List, Optional

class StorageInfoRequest(BaseModel):
    workspaceIds: Optional[List[str]] = None
    workspaceType: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "workspaceIds": ["1234", "abcd", "12ab"],
                "workspaceType": "eMSL"
            }
        }
