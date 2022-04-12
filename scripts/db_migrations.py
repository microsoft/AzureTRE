#!/usr/local/bin/python3

from datetime import datetime
import os
from azure.cosmos.cosmos_client import CosmosClient
from azure.cosmos import PartitionKey
import json
import uuid


class TRECosmosDBMigrations:

    def __init__(self):

        url = os.environ['STATE_STORE_ENDPOINT']
        key = os.environ['STATE_STORE_KEY']
        self.client = CosmosClient(url=url, credential=key)
        self.database = self.client.get_database_client(database=os.environ['COSMOSDB_DATABASE_NAME'])

    def renameCosmosDBFields(self, container_name, old_field_name, new_field_name):

        container = self.database.get_container_client(container_name)

        for item in container.query_items(query='SELECT * FROM c', enable_cross_partition_query=True):
            print(json.dumps(item, indent=True))
            if old_field_name in item:
                item[new_field_name] = item[old_field_name]
                del item[old_field_name]
                container.upsert_item(item)

    def moveDeploymentsToOperations(self, resources_container_name, operations_container_name):
        resources_container = self.database.get_container_client(resources_container_name)

        # create operations container if needed
        self.database.create_container_if_not_exists(id=operations_container_name, partition_key=PartitionKey(path="/id"))
        operations_container = self.database.get_container_client(operations_container_name)

        for item in resources_container.query_items(query='SELECT * FROM c', enable_cross_partition_query=True):
            isActive = True
            if ("deployment" in item):
                newOperation = {
                    "id": str(uuid.uuid4()),
                    "resourceId": item["id"],
                    "status": item["deployment"]["status"],
                    "message": item["deployment"]["message"],
                    "resourceVersion": 0,
                    "createdWhen": datetime.utcnow().timestamp(),
                    "updatedWhen": datetime.utcnow().timestamp()
                }
                operations_container.create_item(newOperation)

                if item["deployment"]["status"] == "deleted":
                    isActive = False

                del item["deployment"]
                item["isActive"] = isActive
                resources_container.upsert_item(item)
                print(f'Moved deployment from resource id {item["id"]} to operations')

    def useSharedServiceTemplateNamesAsIds(self, container_name):
        container = self.database.get_container_client(container_name)

        for item in container.query_items(query='SELECT * FROM c WHERE c.resourceType = "shared-service"', enable_cross_partition_query=True):
            if item["id"] != item["templateName"]:
                newItem = {**item}
                newItem["id"] = item["templateName"]

                container.upsert_item(newItem)
                print(f'Shared service that previously had id {item["id"]} now has id {item["templateName"]}')
                container.delete_item(item, partition_key=item["id"])
                print(f'Deleted shared service with id {item["id"]}')


def main():
    migrations = TRECosmosDBMigrations()
    # PR 1030
    migrations.renameCosmosDBFields("Resources", 'resourceTemplateName', 'templateName')
    migrations.renameCosmosDBFields("Resources", 'resourceTemplateVersion', 'templateVersion')
    migrations.renameCosmosDBFields("Resources", 'resourceTemplateParameters', 'properties')

    # PR 1031
    migrations.renameCosmosDBFields("Resources", 'workspaceType', 'templateName')
    migrations.renameCosmosDBFields("Resources", 'workspaceServiceType', 'templateName')
    migrations.renameCosmosDBFields("Resources", 'userResourceType', 'templateName')

    # Operations History
    migrations.moveDeploymentsToOperations("Resources", "Operations")

    # PR ??
    migrations.useSharedServiceTemplateNamesAsIds("Resources")


if __name__ == "__main__":
    main()
