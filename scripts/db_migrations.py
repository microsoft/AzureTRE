#!/usr/local/bin/python3

import os
from azure.cosmos.cosmos_client import CosmosClient


class TRECosmosDBMigrations:

    def __init__(self):

        url = os.environ['STATE_STORE_ENDPOINT']
        key = os.environ['STATE_STORE_KEY']
        self.client = CosmosClient(url=url, credential=key)
        self.database = self.client.get_database_client(database=os.environ['COSMOSDB_ACCOUNT_NAME'])

    def renameCosmosDBFields(self, container_name, old_field_name, new_field_name):

        container = self.database.get_container_client(container_name)

        import json
        for item in container.query_items(query=f'SELECT * FROM {container_name}', enable_cross_partition_query=True):
            print(json.dumps(item, indent=True))
            if old_field_name in item:
                item[new_field_name] = item[old_field_name]
                del item[old_field_name]
                container.upsert_item(item)


def main():
    migrations = TRECosmosDBMigrations()
    migrations.renameCosmosDBFields("Resources", 'resourceTemplateName', 'templateName')
    migrations.renameCosmosDBFields("Resources", 'resourceTemplateVersion', 'templateVersion')
    migrations.renameCosmosDBFields("Resources", 'resourceTemplateParameters', 'properties')


if __name__ == "__main__":
    main()
