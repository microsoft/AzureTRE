from typing import List
from pydantic import BaseModel

class EmslWorkspace(BaseModel):
    id:str
    display_name:str

class EmslWorkspaceList(BaseModel):
    workspaces:List[EmslWorkspace]
