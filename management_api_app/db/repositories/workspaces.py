from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from models.domain.workspaces import Workspace


class WorkspaceRepository(BaseRepository):
    def update_workspace(self, workspace, param):
        pass

    def remove_workspace(self, target_workspace):
        pass

    def get_workspace_by_workspace_id(self, workspace_id: str) -> Workspace:
        raise EntityDoesNotExist(f"Workspace with id {workspace_id} does not exist")
