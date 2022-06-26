import os
import unittest
from unittest.mock import Mock, MagicMock, patch
from unittest.mock import create_autospec
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.storage.v2021_09_01.aio.operations import StorageAccountsOperations
from azure.mgmt.storage.v2021_09_01.models import StorageAccountListKeysResult, StorageAccountKey
from azure.storage.blob import BlobServiceClient

from shared_code.blob_operations import get_storage_management_client, get_storage_connection_string, create_container, \
    get_blob_client_by_rg_and_account, StorageConnectionMetadata


class TestBlobOperations(unittest.TestCase):
    def test_get_storage_management_client_raises_error_when_subscription_is_undefined(self):
        self.assertRaises(KeyError, get_storage_management_client)

    def test_get_storage_management_client_returns_as_expected(self):
        os.environ.setdefault("AZURE_SUBSCRIPTION_ID", "asss")
        self.assertIsInstance(get_storage_management_client(), StorageManagementClient)

    def test_get_storage_connection_string_has_access_key_as_expected(self):
        storage_management_client = Mock(StorageManagementClient)
        storage_management_client.storage_accounts = Mock(StorageAccountsOperations)

        sa_keys_result= StorageAccountListKeysResult()
        key1 = StorageAccountKey()
        key1.key_name = "key1"
        key1.value = "accountKey1"

        key2 = StorageAccountKey()
        key2.key_name = "key2"
        key2.value = "accountKey2"

        sa_keys_result.keys = [key1, key2]
        storage_management_client.storage_accounts.list_keys = MagicMock(return_value=sa_keys_result)

        self.assertEquals(get_storage_connection_string("sa_name","rg1", storage_management_client).connection_string,
                          "DefaultEndpointsProtocol=https;EndpointSuffix=core.windows.net;AccountName=sa_name;AccountKey=accountKey1")

    @patch('shared_code.blob_operations.get_blob_client_by_rg_and_account', return_value=Mock(BlobServiceClient))
    def test_create_container_creates_container_with_valid_name(self, get_blob_client_by_rg_and_account_mock):
        request_id = "c4b39v99-6d96-4395-8e3b-bef891e3d6b4"

        storage_management_client = Mock(StorageManagementClient)
        storage_management_client.storage_accounts = Mock(StorageAccountsOperations)

        sa_keys_result = StorageAccountListKeysResult()
        key1 = StorageAccountKey()
        key1.key_name = "key1"
        key1.value = "accountKey1"

        sa_keys_result.keys = [key1]
        storage_management_client.storage_accounts.list_keys = MagicMock(return_value=sa_keys_result)

        blob_service_client_mock = get_blob_client_by_rg_and_account_mock("sa_rg_name", "sa_account_name", storage_management_client)
        create_container("sa_rg_name", "sa_account_name", request_id, storage_management_client)
        blob_service_client_mock.create_container.assert_called_with(request_id)

    @patch('shared_code.blob_operations.get_storage_connection_string', return_value=StorageConnectionMetadata("sa", "rg", "DefaultEndpointsProtocol=https;EndpointSuffix=core.windows.net;AccountName=sa;AccountKey=accountKey1"))
    def test_get_blob_client_by_rg_and_account(self, get_storage_connection_string_mock):
        account_name = "sa"
        account_rg = "rg"
        storage_client_mock = Mock(StorageManagementClient)
        blob_service_client = get_blob_client_by_rg_and_account(account_rg, account_name, storage_client_mock)
        get_storage_connection_string_mock.called_once_with(account_rg, account_name, storage_client_mock)
        self.assertEqual(blob_service_client.account_name, account_name)
