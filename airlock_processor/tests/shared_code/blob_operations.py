import os
import unittest
from unittest.mock import Mock, MagicMock
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.storage.v2021_09_01.aio.operations import StorageAccountsOperations
from azure.mgmt.storage.v2021_09_01.models import StorageAccountListKeysResult, StorageAccountKey
from azure.storage.blob import BlobServiceClient

from shared_code.blob_operations import get_storage_management_client, get_storage_connection_string, create_container


class TestBlobOperations(unittest.TestCase):
    def test_get_storage_management_client_raises_error_when_subscription_is_undefined(self):
        self.assertRaises(KeyError, get_storage_management_client)

    def test_get_storage_management_client_returns_as_expected(self):
        os.environ.setdefault("AZURE_SUBSCRIPTION_ID", "asss")
        self.assertIsInstance(get_storage_management_client(), StorageManagementClient)

    def test_get_storage_connection_string_has_access_key_as_expected(self):
        storage_management_client = Mock(StorageManagementClient)
        storage_management_client.storage_accounts = Mock(StorageAccountsOperations)

        a= StorageAccountListKeysResult()
        key1 = StorageAccountKey()
        key1.key_name = "key1"
        key1.value = "accountKey1"

        key2 = StorageAccountKey()
        key2.key_name = "key2"
        key2.value = "accountKey2"

        a.keys = [key1, key2]
        storage_management_client.storage_accounts.list_keys = MagicMock(return_value=a)

        self.assertEquals(get_storage_connection_string("sa_name","rg1", storage_management_client).connection_string,
                          "DefaultEndpointsProtocol=https;EndpointSuffix=core.windows.net;AccountName=sa_name;AccountKey=accountKey1")

    def test_create_container_creates_container_with_valid_name(self):
        request_id = "c4b39v99-6d96-4395-8e3b-bef891e3d6b4"
        blob_client_mock = Mock(BlobServiceClient)
        create_container(blob_client_mock, request_id)
        blob_client_mock.create_container.assert_called_with(request_id)


