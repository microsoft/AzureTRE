from pydantic import BaseModel
from typing import List

class StorageInfoRequest(BaseModel):
    workspaceIds: List[str]
    workspaceType: str

    class Config:
        schema_extra = {
            "example": {
                "workspaceIds": ["1234", "abcd", "12ab"],
                "workspaceType": "eMSL"
            }
        }
