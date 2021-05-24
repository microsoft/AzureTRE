from fastapi import APIRouter, Depends

from api.dependencies.workspaces import get_workspace_by_workspace_id_from_path
from models.domain.workspaces import Workspace
from models.schemas.workspaces import WorkspaceInResponse


router = APIRouter()


@router.get("workspaces/{workspace_id}", response_model=WorkspaceInResponse, name="workspaces:get-workspace")
async def retrieve_workspace_by_workspace_id(
        workspace: Workspace = Depends(get_workspace_by_workspace_id_from_path)
) -> WorkspaceInResponse:
    return WorkspaceInResponse(workspace=workspace)


"""
@router.put("workspaces/{workspace_id}", reponse_model=WorkspaceInResponse, name="workspaces:update-workspace")
async def update_workspace(
        workspace_update: WorkspaceInUpdate = Body(..., embed=True, alias="workspace"),
        current_workspace: Workspace = Depends(get_workspace_by_workspace_id_from_path),
        workspaces_repo: WorkspaceRepository = Depends(get_repository(WorkspaceRepository))
) -> WorkspaceInResponse:
    workspace = await workspaces_repo.update_workspace(workspace=current_workspace, **workspace_update.dict())


@router.delete("workspaces/{workspace_id}", response_model=WorkspaceInResponse, name="workspaces:delete-workspace")
async def delete_workspace(
        workspace: Workspace = Depends(get_workspace_by_workspace_id_from_path),
        workspaces_repo: WorkspaceRepository = Depends(get_repository(WorkspaceRepository))
) -> WorkspaceInResponse:
    await workspaces_repo.remove_workspace(target_workspace=workspace)
"""


# @router.get("/workspaces")
# @router.get("workspaces/{workspace_id}/operations")
# @router.get("/workspaces/{workspaceId}/operations/{operationId}")
# @router.get("/workspaces/{workspaceId}/users")
# @router.post("/workspaces/{workspaceId}/users")
# @router.delete("/workspaces/{workspaceId}/users/{userIdOrEmailToRemove}")
# @router.delete("/workspaces/{workspaceId}/services/{serviceId}")
# @router.get("/workspaces/{workspaceId}/services/{serviceId}")
# @router.get("/workspaces/{workspaceId}/services/{serviceId}/operations")
# @router.get("/workspaces/{workspaceId}/services/{serviceId}/operations/{operationId}")
# @router.get("/workspaces/{workspaceId}/services/{serviceId}/users")
# @router.post("/workspaces/{workspaceId}/services/{serviceId}/users")
# @router.delete("/workspaces/{workspaceId}/services/{serviceId}/users/{userIdOrEmailToRemove}")
# @router.get("/workspaces/{workspaceId}/services/{serviceId}/actions/{actionId}")
# @router.get("/workspaces/{workspaceId}/services/{serviceId}/actions")
# @router.get("/workspaces/{workspaceId}/services/{serviceId}/actions/{actionId}/operations")
# @router.get("/workspaces/{workspaceId}/services/{serviceId}/actions/{actionId}/operations/{operationId}")
# @router.post("/workspaces/{workspaceId}/services/{serviceId}/actions")
# @router.put("/workspaces/{workspaceId}/services/{serviceId}")
# @router.get("/workspaces/{workspaceId}/services")
# @router.post("/workspaces/{workspaceId}/services")
