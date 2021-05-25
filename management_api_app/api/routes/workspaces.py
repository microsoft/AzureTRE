from fastapi import APIRouter, Depends

from api.dependencies.workspaces import get_workspace_by_workspace_id_from_path
from models.domain.resource import Resource
from models.schemas.resource import ResourceInResponse


router = APIRouter()


@router.get("/workspaces/{workspace_id}", response_model=ResourceInResponse, name="workspaces:get-workspace")
async def retrieve_workspace_by_workspace_id(
        workspace: Resource = Depends(get_workspace_by_workspace_id_from_path)
) -> ResourceInResponse:
    return ResourceInResponse(resource=workspace)
