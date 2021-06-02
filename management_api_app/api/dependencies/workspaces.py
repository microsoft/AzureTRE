from fastapi import Depends, HTTPException, Path
from pydantic import UUID4
from starlette.status import HTTP_404_NOT_FOUND

from db.errors import EntityDoesNotExist
from db.repositories.workspaces import WorkspaceRepository
from api.dependencies.database import get_repository
from models.domain.workspace import Workspace
from resources import strings


async def get_workspace_by_workspace_id_from_path(workspace_id: UUID4 = Path(...), workspaces_repo: WorkspaceRepository = Depends(get_repository(WorkspaceRepository))) -> Workspace:
    try:
        return workspaces_repo.get_workspace_by_workspace_id(workspace_id)
    except EntityDoesNotExist:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_DOES_NOT_EXIST)
