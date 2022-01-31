from datetime import datetime
import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as
from starlette.types import Message
from core import config
from db.repositories.base import BaseRepository

from db.errors import EntityDoesNotExist
from models.domain.operation import Operation, Status


class OperationRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_OPERATIONS_CONTAINER)

    @staticmethod
    def operations_query():
        return 'SELECT * FROM c WHERE'

    def create_operation_item(self, resource_id: str, status: Status, message: str, resource_path: str) -> Operation:
        operation_id = str(uuid.uuid4())

        timestamp = datetime.utcnow().timestamp()
        operation = Operation(
            id=operation_id,
            resourceId=resource_id,
            resourcePath=resource_path,
            status=status,
            resourceVersion=0, # Resource versioning coming in future
            createdWhen=timestamp,
            updatedWhen=timestamp,
            message=message
        )

        self.save_item(operation)
        return operation

    def update_operation_status(self, operation_id: str, status: Status, message: str) -> Operation:
        operation = self.get_operation_by_id(operation_id)

        operation.status = status
        operation.message = message
        operation.updatedWhen = datetime.utcnow().timestamp()

        self.update_item(operation)
        return operation

    def get_operation_by_id(self, operation_id: str) -> Operation:
        """
        returns a single operation doc
        """
        query = self.operations_query() + f' c.id = "{operation_id}"'
        operation = self.query(query=query)
        if not operation:
            raise EntityDoesNotExist
        return parse_obj_as(Operation, operation[0])

    def get_operations_by_resource_id(self, resource_id: str) -> List[Operation]:
        """
        returns a list of operations for this resource
        """
        query = self.operations_query() + f' c.resourceId = "{resource_id}"'
        operations = self.query(query=query)
        return parse_obj_as(List[Operation], operations)

    def resource_has_deployed_operation(self, resource_id: str) -> bool:
        """
        checks whether this resource has a successful "deployed" operation
        """
        query = self.operations_query() + f' c.resourceId = "{resource_id}" AND c.status = "{Status.Deployed}"'
        operations = self.query(query=query)
        return len(operations) > 0
