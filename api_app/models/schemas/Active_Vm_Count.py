from typing import List
from pydantic import BaseModel

class WorkspaceIds(BaseModel):
    workspace_ids: List[str]

class ResourceCount(BaseModel):
    totalCount: int
    activeCount: int
