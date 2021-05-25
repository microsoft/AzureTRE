from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from models.domain.resource import Resource


class WorkspaceRepository(BaseRepository):

    def get_workspace_by_workspace_id(self, workspace_id: str) -> Resource:
        raise EntityDoesNotExist(f"Workspace with id {workspace_id} does not exist")
