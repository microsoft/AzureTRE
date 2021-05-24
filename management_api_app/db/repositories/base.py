from azure.cosmos import CosmosClient


class BaseRepository:
    def __init__(self, client: CosmosClient) -> None:
        self._client = client

    @property
    def client(self) -> CosmosClient:
        return self._client
