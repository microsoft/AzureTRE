import datetime, logging, math
from models.domain.data_usage import MHRAWorkspaceDataUsage, MHRAContainerUsageItem, MHRAFileshareUsageItem, MHRAStorageAccountLimits, MHRAStorageAccountLimitsItem, StorageAccountLimitsInput
from core import config, credentials
from resources import constants, strings
from functools import lru_cache
from fastapi import HTTPException, status
from azure.data.tables import TableServiceClient, UpdateMode

# make sure CostService is singleton
@lru_cache(maxsize=None)
class DataUsageService:
    scope: str
    account_endpoint: str
    client: TableServiceClient
    RATE_LIMIT_RETRY_AFTER_HEADER_KEY: str = "x-ms-ratelimit-microsoft.costmanagement-entity-retry-after"
    SERVICE_UNAVAILABLE_RETRY_AFTER_HEADER_KEY: str = "Retry-After"

    def __init__(self) -> None:
        self.scope = "/subscriptions/{}".format(config.SUBSCRIPTION_ID)
        self.account_name = constants.STORAGE_ACCOUNT_NAME_CORE_RESOURCE_GROUP.format(config.TRE_ID)
        self.account_endpoint = f"https://{self.account_name}.table.core.windows.net"
        # We add a custom ClientType header to avoid small limits for Azure API calls.
        self.client = TableServiceClient(
            endpoint=self.account_endpoint,
            credential=credentials.get_credential(),
            headers={"ClientType": config.CLIENT_TYPE_CUSTOM_HEADER}
        )

    async def get_workspace_data_usage(self) -> MHRAWorkspaceDataUsage:
        container_usage_table = constants.WORKSPACE_CONTAINER_USAGE_TABLE_NAME
        fileshare_usage_table = constants.WORKSPACE_FILESHARE_USAGE_TABLE_NAME

        try:
            container_usage_items = []
            fileshare_usage_items = []

            # For performing this operation, the identity used for running the API must have the role
            # "Storage Table Data Reader" (the scope is the storage account holding the table).
            table_client = self.client.get_table_client(table_name=container_usage_table)
            entities = table_client.list_entities()

            for entity in entities:
                container_usage_items.append(
                    MHRAContainerUsageItem(
                        workspace_name=entity['WorkspaceName'],
                        storage_name=entity['StorageName'],
                        storage_usage=entity['StorageUsage'],
                        storage_limits=entity['StorageLimits'],
                        storage_limits_update_time=entity['StorageLimitsUpdateTime'],
                        storage_percentage_used=entity['StoragePercentage'],
                        update_time=entity['UpdateTime']
                    )
                )

            # For performing this operation, the identity used for running the API must have the role
            # "Storage Table Data Reader" (the scope is the storage account holding the table).
            table_client = self.client.get_table_client(table_name=fileshare_usage_table)
            entities = table_client.list_entities()

            for entity in entities:
                fileshare_usage_items.append(
                    MHRAFileshareUsageItem(
                        workspace_name=entity['WorkspaceName'],
                        storage_name=entity['StorageName'],
                        fileshare_usage=entity['FileshareUsage'],
                        fileshare_limits=entity['FileshareLimits'],
                        fileshare_limits_update_time=entity['FileshareLimitsUpdateTime'],
                        fileshare_percentage_used=entity['FilesharePercentage'],
                        update_time=entity['UpdateTime']
                    )
                )

            return MHRAWorkspaceDataUsage(workspace_container_usage_items=container_usage_items,workspace_fileshare_usage_items=fileshare_usage_items)

        except HttpResponseError:
            logging.exception("HTTP error when calling table_client.")
            raise HttpResponseError
        except:
            logging.exception("Unknown error when calling table_client.")
            raise Exception("Unknown error when calling table_client.")

    async def get_storage_account_limits(self) -> MHRAStorageAccountLimits:
        container_usage_table = constants.WORKSPACE_CONTAINER_USAGE_TABLE_NAME

        try:
            storage_account_limits_items = []

            # For performing this operation, the identity used for running the API must have the role
            # "Storage Table Data Reader" (the scope is the storage account holding the table).
            table_client = self.client.get_table_client(table_name=container_usage_table)
            entities = table_client.list_entities()

            for entity in entities:
                storage_account_limits_items.append(
                    MHRAStorageAccountLimitsItem(
                        workspace_name=entity['WorkspaceName'],
                        storage_name=entity['StorageName'],
                        storage_limits=entity['StorageLimits'],
                        storage_limits_update_time=entity['StorageLimitsUpdateTime']
                    )
                )

            return MHRAStorageAccountLimits(storage_account_limits_items=storage_account_limits_items)

        except HttpResponseError:
            logging.exception("HTTP error when calling table_client.")
            raise HttpResponseError
        except:
            logging.exception("Unknown error when calling table_client.")
            raise Exception("Unknown error when calling table_client.")

    async def set_storage_account_limits(self, storage_account_lits_properties: StorageAccountLimitsInput) -> MHRAStorageAccountLimitsItem:
        storage_limits_update_time = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
        container_usage_table = constants.WORKSPACE_CONTAINER_USAGE_TABLE_NAME

        try:
            # Creating filter for selecting the correct storage account
            workspace_name = storage_account_lits_properties.workspace_name
            storage_name = storage_account_lits_properties.storage_name
            storage_limits = storage_account_lits_properties.storage_limits

            # Control new limits.
            if storage_limits < 0:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=strings.DATA_USAGE_LIMITS_MUST_BE_POSITIVE)

            # For performing this operation, the identity used for running the API must have the role
            # "Storage Table Data Reader" (the scope is the storage account holding the table).
            table_client = self.client.get_table_client(table_name=container_usage_table)

            parameters = {"workspacename": workspace_name, "storagename": storage_name}
            workspace_filter = "WorkspaceName eq @workspacename and StorageName eq @storagename"

            # Filter table entities using workspace name and storage account name.
            entities = table_client.query_entities(
                query_filter=workspace_filter,
                parameters=parameters
            )

            # Fail if entity is not found
            entities_list = list(entities)
            if len(list(entities_list)) == 0:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=strings.DATA_USAGE_WORKSPACE_OR_STORAGE_ACCOUNT_NOT_FOUND)

            # Only 1 interation should happen.
            for entity in entities_list:
                # Create a new entity to replace the old one.
                new_entity = {
                    "PartitionKey": entity['PartitionKey'],
                    "RowKey": entity['RowKey'],
                    "WorkspaceName": entity['WorkspaceName'],
                    "StorageName": entity['StorageName'],
                    "StorageUsage": entity['StorageUsage'],
                    "StorageLimits": storage_limits,
                    "StorageLimitsUpdateTime": storage_limits_update_time,
                    "StoragePercentage": math.floor(((entity['StorageUsage'] * 100.0) / storage_limits)),
                    "UpdateTime": entity['UpdateTime']
                }

                logging.info(f"Updating data limits for storage account {entity['StorageName']} - New limit: {storage_limits} - Timestamp: {storage_limits_update_time}")

                # Merge the entity
                table_client.update_entity(mode=UpdateMode.MERGE, entity=new_entity)

            storage_account_limit_item = MHRAStorageAccountLimitsItem(
                workspace_name=workspace_name,
                storage_name=storage_name,
                storage_limits=storage_limits,
                storage_limits_update_time=storage_limits_update_time
            )

            return storage_account_limit_item

        except:
            logging.exception("Unknown error when calling table_client.")
            raise Exception("Unknown error when calling table_client.")

@lru_cache(maxsize=None)
def data_usage_service_factory() -> DataUsageService:
    return DataUsageService()
