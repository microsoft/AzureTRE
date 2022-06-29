import logging
import uuid
from azure.cosmos import CosmosClient
from db.errors import EntityDoesNotExist
from db.repositories.operations import OperationRepository
from db.repositories.resources import ResourceRepository


class ResourceMigration(ResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    def add_deployment_status_field(self, operations_repository: OperationRepository) -> int:

        i = 0
        for op in operations_repository.query("SELECT * from c ORDER BY c._ts ASC"):
            try:
                resource = self.get_resource_by_id(uuid.UUID(op['resourceId']))
                if resource.deploymentStatus != op['status']:
                    resource.deploymentStatus = op['status']
                    self.update_item(resource)
                    i = i + 1
            except EntityDoesNotExist:
                logging.info(f'Resource Id {op["resourceId"]} not found')
                # ignore errors and try the next one

        return i
