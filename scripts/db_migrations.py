#!/usr/local/bin/python3

from datetime import datetime
import os
from azure.cosmos.cosmos_client import CosmosClient
from azure.mgmt.cosmosdb import CosmosDBManagementClient
from azure.cosmos import PartitionKey
from azure.identity import DefaultAzureCredential
import json
import semantic_version
import uuid

STATE_STORE_DATABASE = "AzureTRE"


class TRECosmosDBMigrations:

    def __init__(self):
        if (self.can_connect_to_cosmos()):
            url = os.environ['STATE_STORE_ENDPOINT']
            key = self.get_store_key()
            self.client = CosmosClient(url=url, credential=key)
            self.database = self.client.get_database_client(STATE_STORE_DATABASE)

    def can_connect_to_cosmos(self) -> bool:
        return os.getenv('ENABLE_LOCAL_DEBUGGING', 'False').lower() in ('true', 1, 't') if 'ENABLE_LOCAL_DEBUGGING' in os.environ else False

    def get_store_key(self) -> str:
        if 'STATE_STORE_KEY' in os.environ:
            primary_master_key = os.getenv('STATE_STORE_KEY')
        else:
            credential = DefaultAzureCredential()
            cosmosdb_client = CosmosDBManagementClient(credential, subscription_id=os.environ['SUBSCRIPTION_ID'])
            database_keys = cosmosdb_client.database_accounts.list_keys(resource_group_name=os.environ['RESOURCE_GROUP_NAME'], account_name=os.environ['COSMOSDB_ACCOUNT_NAME'])
            primary_master_key = database_keys.primary_master_key

        return primary_master_key

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

    def deleteDuplicatedSharedServices(self, resource_container_name):
        resources_container = self.database.get_container_client(resource_container_name)

        template_names = ['tre-shared-service-firewall', 'tre-shared-service-nexus', 'tre-shared-service-gitea']

        for template_name in template_names:
            for item in resources_container.query_items(query=f'SELECT * FROM c WHERE c.resourceType = "shared-service" AND c.templateName = "{template_name}" \
                                                                ORDER BY c.updatedWhen ASC OFFSET 1 LIMIT 10000', enable_cross_partition_query=True):
                print(f"Deleting element {item}")
                resources_container.delete_item(item, partition_key=item["id"])

    def moveAuthInformationToProperties(self, resources_container_name):
        resources_container = self.database.get_container_client(resources_container_name)

        for item in resources_container.query_items(query='SELECT * FROM c', enable_cross_partition_query=True):
            template_version = semantic_version.Version(item["templateVersion"])
            updated = False
            if (template_version < semantic_version.Version('0.2.9') and item["templateName"] == "tre-workspace-base"):

                # Rename app_id to be client_id
                if "app_id" in item["properties"]:
                    item["properties"]["client_id"] = item["properties"]["app_id"]
                    del item["properties"]["app_id"]
                    updated = True

                if "scope_id" not in item["properties"]:
                    item["properties"]["scope_id"] = item["properties"]["client_id"]
                    updated = True

                if "authInformation" in item:
                    print(f'Upgrading authInformation in workspace {item["id"]}')

                    if "app_id" in item["authInformation"]:
                        del item["authInformation"]["app_id"]

                    # merge authInformation into properties
                    item["properties"] = {**item["authInformation"], **item["properties"]}
                    del item["authInformation"]
                    updated = True

                if updated:
                    resources_container.upsert_item(item)
                    print(f'Upgraded authentication for workspace id {item["id"]}')


def main():
    migrations = TRECosmosDBMigrations()
    if not migrations.can_connect_to_cosmos():
        print('You cannot migrate the cosmos database without setting ENABLE_LOCAL_DEBUGGING to true.')
    else:
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

        # Shared services (PR #1717)
        migrations.deleteDuplicatedSharedServices("Resources")

        # Authentication needs to be in properties so we can update them. (PR #1726)
        migrations.moveAuthInformationToProperties("Resources")


if __name__ == "__main__":
    main()
