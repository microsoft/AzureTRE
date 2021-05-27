from azure.cosmos import DatabaseProxy


class BaseRepository:
    def __init__(self, database: DatabaseProxy) -> None:
        self._database = database

    @property
    def database(self) -> DatabaseProxy:
        return self._database
