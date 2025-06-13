from datetime import datetime, timedelta, date
from typing import List, Optional
from pydantic import BaseModel, Field

class StorageAccountLimitsInput(BaseModel):
    workspace_name: str = Field(title="Workspace name to be updated")
    storage_name: str = Field(title="Storage Account name to be updated")
    storage_limits: float = Field(title="New Storage Account storage limits")

    class Config:
        schema_extra = {
            "example": {
                "workspace_name": "rg-cprdtest-ws-6c77",
                "storage_name": "stgws6c77",
                "storage_limits": 5000
            }
        }

class MHRAStorageAccountLimitsItem(BaseModel):
    workspace_name: str
    storage_name: str
    storage_limits: float
    storage_limits_update_time: str

class MHRAStorageAccountLimits(BaseModel):
    storage_account_limits_items: List[MHRAStorageAccountLimitsItem]

class MHRAContainerUsageItem(BaseModel):
    workspace_name: str
    storage_name: str
    storage_usage: float
    storage_limits: float
    storage_limits_update_time: str
    storage_percentage_used: float
    update_time: str

class MHRAFileshareUsageItem(BaseModel):
    workspace_name: str
    storage_name: str
    fileshare_usage: float
    fileshare_limits: float
    fileshare_limits_update_time: str
    fileshare_percentage_used: float
    update_time: str

class MHRAWorkspaceDataUsage(BaseModel):
    workspace_container_usage_items: List[MHRAContainerUsageItem]
    workspace_fileshare_usage_items: List[MHRAFileshareUsageItem]
