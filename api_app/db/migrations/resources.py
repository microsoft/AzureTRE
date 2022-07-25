from azure.cosmos import CosmosClient
from db.repositories.operations import OperationRepository
from db.repositories.resources import ResourceRepository


class ResourceMigration(ResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    def add_deployment_status_field(self, operations_repository: OperationRepository) -> int:
        num_updated = 0
        for resource in self.query("SELECT * from c WHERE NOT IS_DEFINED(c.deploymentStatus)"):
            # For each resource, find the last operation, if it exists
            id = resource['id']
            op = operations_repository.query(f'SELECT * from c WHERE c.resourceId = "{id}" ORDER BY c._ts DESC OFFSET 0 LIMIT 1')
            if op:
                # Set the deploymentStatus of the resource to be the status fo its last operation
                resource['deploymentStatus'] = op[0]['status']
                self.update_item_dict(resource)
                num_updated = num_updated + 1

        return num_updated
