from azure.cosmos import DatabaseProxy, CosmosClient

from core import config


class BaseRepository:
    def __init__(self, client: CosmosClient) -> None:
        self._client = client
        if self._client:
            self._database = client.get_database_client(config.STATE_STORE_DATABASE)
        else:
            self._database = None

    @property
    def database(self) -> DatabaseProxy:
        return self._database
