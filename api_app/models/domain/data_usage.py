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
    workspace_name: Optional[str] = None
    storage_name: Optional[str] = None
    storage_usage: Optional[str] = None
    storage_limits: Optional[str] = None
    storage_remaining: Optional[str] = None
    storage_limits_update_time: Optional[str] = None
    storage_percentage_used: Optional[float] = None
    update_time: Optional[str] = None


class MHRAFileshareUsageItem(BaseModel):
    workspace_name: Optional[str] = None
    storage_name: Optional[str] = None
    fileshare_usage:  Optional[str] = None
    fileshare_limits:  Optional[str] = None
    fileshare_remaining:  Optional[str] = None
    fileshare_limits_update_time: str
    fileshare_percentage_used:  Optional[float] = None
    update_time: Optional[str] = None

class MHRAWorkspaceDataUsage(BaseModel):
    workspace_container_usage_items: List[MHRAContainerUsageItem]
    workspace_fileshare_usage_items: List[MHRAFileshareUsageItem]

class WorkspaceDataUsage(BaseModel):
    container_usage_item: MHRAContainerUsageItem
    fileshare_usage_item: Optional[MHRAFileshareUsageItem] = None

class MHRAProtocolItem(BaseModel):
    workspace_name: Optional[str] = None
    storage_name: Optional[str] = None
    protocol_id: Optional[str] = None
    protocol_data_usage: Optional[str] = None
    protocol_percentage_used: Optional[float] = None

class MHRAProtocolList(BaseModel):
    protocol_items: List[MHRAProtocolItem]
