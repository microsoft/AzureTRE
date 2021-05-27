from azure.cosmos import ContainerProxy, DatabaseProxy

from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from models.domain.resource import Resource


class WorkspaceRepository(BaseRepository):
    def __init__(self, database: DatabaseProxy):
        super().__init__(database)
        print(database)
        self._container = None
        # self._container = database.create_container_if_not_exists(id="/Resources", partition_key=PartitionKey(path="/appId"))
        # print(self.container)

    @property
    def container(self) -> ContainerProxy:
        return self._container

    def get_workspace_by_workspace_id(self, workspace_id: str) -> Resource:
        raise EntityDoesNotExist(f"Workspace with id {workspace_id} does not exist")

    def get_all_active_resources(self):
        # query = "SELECT * from c"
        # workspaces = list(self.container.query_items(query=query, enable_cross_partition_query=True))
        # logging.debug(workspaces)
        # return workspaces
        return []
