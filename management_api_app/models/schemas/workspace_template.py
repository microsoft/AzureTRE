from typing import List
from pydantic import BaseModel


class WorkspaceTemplateNamesInList(BaseModel):
    templateNames: List[str]

    class Config:
        schema_extra = {
            "example": {
                "templateNames": ["tre-workspace-vanilla", "tre-workspace-base"]
            }
        }
