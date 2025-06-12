from datetime import datetime, timedelta, date
from typing import List, Optional
from pydantic import BaseModel

class MHRAStorageAccountLimit(BaseModel):
    workspace_name: str
    storage_name: str
    storage_limits: float
    storage_limits_update_time: str

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
