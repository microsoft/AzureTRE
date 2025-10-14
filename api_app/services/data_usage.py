import datetime, logging, math
import uuid

import httpx
from db.repositories.workspaces import WorkspaceRepository
from models.schemas.container_reation_request import ContainerCreateRequest, EntraGroup, EntraGroupReuest, RoleAssignmentRequest
from models.domain.data_usage import MHRAProtocolItem, MHRAProtocolList, MHRAWorkspaceDataUsage, MHRAContainerUsageItem, MHRAFileshareUsageItem, MHRAStorageAccountLimits, MHRAStorageAccountLimitsItem, StorageAccountLimitsInput, WorkspaceDataUsage
from models.schemas.storage_info_request import StorageInfoRequest
from core import config, credentials
from resources import constants, strings
from functools import lru_cache
from fastapi import HTTPException, status
from azure.data.tables import TableServiceClient, UpdateMode
from azure.storage.blob import BlobServiceClient
from msgraph import GraphServiceClient
from msgraph.generated.models.group import Group
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from azure.mgmt.authorization import AuthorizationManagementClient
from azure.mgmt.storage import StorageManagementClient

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
                        storage_remaining=entity['StorageLimits']-entity['StorageUsage'],
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
                        fileshare_remaining=entity['FileshareLimits']-entity['FileshareUsage'],
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

    async def get_workspace_storage_info(self, storage_info_request: StorageInfoRequest) -> MHRAWorkspaceDataUsage:
        container_usage_table = constants.WORKSPACE_CONTAINER_USAGE_TABLE_NAME
        fileshare_usage_table = constants.WORKSPACE_FILESHARE_USAGE_TABLE_NAME

        try:
            container_usage_items = []
            fileshare_usage_items = []


            query_filter = " and ".join([f"WorkspaceName eq '{workspaceId}'" for workspaceId in storage_info_request.workspaceIds])

            # For performing this operation, the identity used for running the API must have the role
            # "Storage Table Data Reader" (the scope is the storage account holding the table).
            table_client = self.client.get_table_client(table_name=container_usage_table)
            entities = table_client.query_entities(query_filter)

            for entity in entities:
                container_usage_items.append(
                    MHRAContainerUsageItem(
                        workspace_name=entity['WorkspaceName'],
                        storage_name=entity['StorageName'],
                        storage_usage=entity['StorageUsage'],
                        storage_limits=entity['StorageLimits'],
                        storage_remaining=entity['StorageLimits']-entity['StorageUsage'],
                        storage_limits_update_time=entity['StorageLimitsUpdateTime'],
                        storage_percentage_used = math.floor(entity['StoragePercentage']),
                        update_time=entity['UpdateTime']
                    )
                )
            if storage_info_request.workspaceType in ["eMSL", "", None]:
                # For performing this operation, the identity used for running the API must have the role
                # "Storage Table Data Reader" (the scope is the storage account holding the table).
                table_client = self.client.get_table_client(table_name=fileshare_usage_table)
                entities = table_client.query_entities(query_filter)

                for entity in entities:
                    fileshare_usage_items.append(
                        MHRAFileshareUsageItem(
                            workspace_name=entity['WorkspaceName'],
                            storage_name=entity['StorageName'],
                            fileshare_usage=entity['FileshareUsage'],
                            fileshare_limits=entity['FileshareLimits'],
                            fileshare_remaining=entity['FileshareLimits']-entity['FileshareUsage'],
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

    async def get_perstudy_items(self, workspaceId: str) -> MHRAProtocolList:
        container_perstudy_table = constants.WORKSPACE_PERSTUDY_USAGE_TABLE_NAME

        try:
            protocol_items = []
            query_filter = f"WorkspaceName eq '{workspaceId}'"
            table_client = self.client.get_table_client(table_name=container_perstudy_table)
            entities = table_client.query_entities(query_filter)

            for entity in entities:
                protocol_items.append(
                    MHRAProtocolItem(
                        workspace_name=entity['WorkspaceName'],
                        storage_name=entity['StorageName'],
                        protocol_id=entity['ProtocolId'],
                        protocol_data_usage = self._format_size(entity.get('ProtocolDataUsage')),
                        protocol_percentage_used = math.floor(entity.get('ProtocolPercentageUsed',0))
                    )
                )

            return MHRAProtocolList(protocol_items=protocol_items)

        except HttpResponseError as e:
            logging.exception("HTTP error when calling table_client.")
            raise
        except Exception as e:
            logging.exception("Unknown error when calling table_client.")
            raise

    async def get_data_usage_for_workspace(self, workspaceId: str) -> WorkspaceDataUsage:
        container_usage_table = constants.WORKSPACE_CONTAINER_USAGE_TABLE_NAME
        fileshare_usage_table = constants.WORKSPACE_FILESHARE_USAGE_TABLE_NAME

        tre_id = config.TRE_ID
        workspace = constants.WORKSPACE_RESOURCE_GROUP_NAME.format(tre_id, workspaceId[-4:])

        try:
            query_filter = f"WorkspaceName eq '{workspace}'"

            # Container usage
            table_client = self.client.get_table_client(table_name=container_usage_table)
            entities = table_client.query_entities(query_filter)

            container_usage_item = None
            if entities:
                for entity in entities:
                    container_usage_item = MHRAContainerUsageItem(
                        workspace_name = entity.get('WorkspaceName', ''),
                        storage_name = entity.get('StorageName', ''),
                        storage_usage = self._format_size(entity.get('StorageUsage')),
                        storage_limits = self._format_size(entity.get('StorageLimits')),
                        storage_remaining = self._format_size(
                            (entity.get('StorageLimits', 0) - entity.get('StorageUsage', 0))
                        ),
                        storage_limits_update_time = entity.get('StorageLimitsUpdateTime', ''),
                        storage_percentage_used = math.floor(entity.get('StoragePercentage', 0)),
                        update_time = entity.get('UpdateTime', '')
                    )
                    break  # Only take the first matching item

            # Fileshare usage
            table_client = self.client.get_table_client(table_name=fileshare_usage_table)
            entities = table_client.query_entities(query_filter)

            fileshare_usage_item = None
            if entities:
                for entity in entities:
                    fileshare_usage_item = MHRAFileshareUsageItem(
                        workspace_name = entity.get('WorkspaceName', ''),
                        storage_name = entity.get('StorageName', ''),
                        fileshare_usage = self._format_size(entity.get('FileshareUsage')),
                        fileshare_limits = self._format_size(entity.get('FileshareLimits')),
                        fileshare_remaining = self._format_size(
                            (entity.get('FileshareLimits', 0) - entity.get('FileshareUsage', 0))
                        ),
                        fileshare_limits_update_time = entity.get('FileshareLimitsUpdateTime', ''),
                        fileshare_percentage_used = math.floor(entity.get('FilesharePercentage', 0)),
                        update_time = entity.get('UpdateTime', '')
                    )
                    break  # Only take the first matching item

            return WorkspaceDataUsage(
                container_usage_item=container_usage_item,
                fileshare_usage_item=fileshare_usage_item
            )

        except HttpResponseError:
            logging.exception("HTTP error when calling table_client.")
            raise
        except Exception:
            logging.exception("Unknown error when calling table_client.")
            raise

    async def create_container(self, container_create_request: ContainerCreateRequest, workspace_repo: WorkspaceRepository):
        workspace = await workspace_repo.get_workspace_by_id(container_create_request.workspaceId)
        account_name = constants.STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP.format(container_create_request.workspaceId[-4:])

        blob_service_client = BlobServiceClient(
            account_url=self.get_account_url(account_name),
            credential=credentials.get_credential()
        )
        container_name = container_create_request.protocolId
        try:
            container_client =  blob_service_client.create_container(container_name)
        except Exception as e:
            raise Exception(f"Error occurred while creating container: {e}")

        template = workspace.templateName
        folder_names = ['Type1/', 'Type2/']
        folderName = "ReceiveFromExplore" if template.endswith("a-msl") else "SendToAnalyse"
        folder_names.append(folderName + '/')

        for folder_name in folder_names:
            try:
                blob_name = f"{folder_name}/.emptyFile"
                container_client.upload_blob(blob_name, b'', overwrite=True)
            except Exception as e:
                raise Exception(f"Error occurred while creating blob folder '{folder_name}': {e}")

        return {"container": container_name, "folders": folder_names}


    def _format_size(self, size_gb):

        if size_gb is None or not isinstance(size_gb, (int, float)) or size_gb < 0:
            return "0.00GB"
        if size_gb < 1024:
            return f"{size_gb:.2f}GB"
        else:
            size_tb = size_gb / 1024
            return f"{size_tb:.2f}TB"

    async def create_group(self, group_request: EntraGroupReuest)->EntraGroup:

        tenant_id = config.AAD_TENANT_ID
        client_id = await self._fetch_key_valut("ssbs-management-app-registration-client-id")
        client_secret = await self._fetch_key_valut("ssbs-management-app-registration-client-secret")

        credential = ClientSecretCredential(
            tenant_id = tenant_id,
            client_id = client_id,
            client_secret = client_secret
        )

        entra_group_name = f"Researcher_Data_Access_{group_request.protocolId}"
        return await self._create_entra_group(credential, entra_group_name)

    async def _create_entra_group(self, credential, entra_group_name: str) -> EntraGroup:
        graph_client = GraphServiceClient(credentials=credential)

        group_data = Group(
            display_name=entra_group_name,
            mail_enabled=False,
            mail_nickname=entra_group_name,
            security_enabled=True
        )

        try:
            created_group = await graph_client.groups.post(group_data)

            group_model = EntraGroup(
                id=created_group.id,
                display_name=created_group.display_name,
                mail_nickname=created_group.mail_nickname,
                security_enabled=created_group.security_enabled
            )

            return group_model

        except httpx.ConnectError as e:
            raise Exception(f"Error creating group: {e}")

    async def _fetch_key_valut(self, secret_name) -> str:
        key_vault_name = constants.CORE_KEYVAULT_NAME.format(config.TRE_ID)
        key_vault_url = f"https://{key_vault_name}.vault.azure.net/"
        credential = credentials.get_credential()
        client = SecretClient(vault_url=key_vault_url, credential=credential)
        retrieved_secret = client.get_secret(secret_name)
        return retrieved_secret.value

    async def assign_role_to_group(self, role_assignment_request: RoleAssignmentRequest):
        subscription_id = config.SUBSCRIPTION_ID
        credential = credentials.get_credential()
        storage_account = await self._get_storage_account(credential,role_assignment_request.workspaceId)
        role_definition_id = await self._get_role_definition_id(credential, subscription_id)

        await self._create_role_assignment(credential, subscription_id, storage_account.id, role_assignment_request.groupId, role_definition_id)

    async def _get_storage_account(self, credential, workspaceId):
        subscription_id = config.SUBSCRIPTION_ID
        storage_account_name = constants.STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP.format(workspaceId)
        resource_group_name = constants.WORKSPACE_RESOURCE_GROUP_NAME.format(config.TRE_ID, workspaceId)
        storage_client = StorageManagementClient(credential, subscription_id)
        try:
            return storage_client.storage_accounts.get_properties(
                resource_group_name=resource_group_name,
                account_name=storage_account_name
            )
        except Exception as e:
            raise Exception(f"Error getting storage account: {e}")

    async def _get_role_definition_id(self, credential, subscription_id):
        authorization_client = AuthorizationManagementClient(credential, subscription_id)
        role_name = 'Workspace Researcher Blob Data Contributor'
        role_definitions = authorization_client.role_definitions.list(
            scope=f"/subscriptions/{subscription_id}"
        )

        role_definition = next((rd for rd in role_definitions if rd.role_name == role_name), None)
        if role_definition is None:
            raise Exception(f"Role definition not found for {role_name}")

        return role_definition.id.split('/')[-1]

    async def _create_role_assignment(self, credential, subscription_id, scope, principal_id, role_definition_id):
        authorization_client = AuthorizationManagementClient(credential, subscription_id)
        role_assignment_name = str(uuid.uuid4())

        action = "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete"
        conditions = [
            ("Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path", "SendToAnalyse"),
            ("Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path", "Type1"),
            ("Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path", "Type2")
        ]

        expression = self._build_expression(action, conditions,"&&")
        logging.info(expression)
        try:
            authorization_client.role_assignments.create(
                scope=scope,
                role_assignment_name=role_assignment_name,
                parameters = {
                    "role_definition_id": f"/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/{role_definition_id}",
                    "principal_id": principal_id,
                    "condition": expression,
                    "condition_version": "2.0"
                }
            )
        except Exception as e:
            raise Exception(f"Error creating role assignment: {e}")

    def _build_expression(self, action, conditions, operator="||"):
        expression_parts = [f"ActionMatches{{'{action}'}}"]
        for attr, val in conditions:
            expression_parts.append(f"NOT@Resource[{attr}] StringEquals '{val}'")
        return f"({f' {operator} '.join(expression_parts)})"

@lru_cache(maxsize=None)
def data_usage_service_factory() -> DataUsageService:
    return DataUsageService()
