from pydantic import BaseModel

from models.domain.workspaces import Workspace


class WorkspaceInResponse(BaseModel):
    workspace: Workspace


"""
class WorkspaceInUpdate:
    pass
"""
