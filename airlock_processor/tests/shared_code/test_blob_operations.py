import os
import unittest
from unittest.mock import Mock, MagicMock, patch

from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.storage.v2021_09_01.aio.operations import StorageAccountsOperations
from azure.mgmt.storage.v2021_09_01.models import StorageAccountListKeysResult, StorageAccountKey
from azure.storage.blob import BlobServiceClient

from shared_code.blob_operations import create_container, get_blob_info_from_topic_and_subject,get_blob_info_from_blob_url

class TestBlobOperations(unittest.TestCase):
    def test_get_blob_info_from_topic_and_subject(self):
        topic = "/subscriptions/SUB_ID/resourceGroups/RG_NAME/providers/Microsoft.Storage/storageAccounts/ST_ACC_NAME"
        subject = "/blobServices/default/containers/CONTAINER_GUID/blobs/BLOB"

        storage_account_name, container_name, blob_name = get_blob_info_from_topic_and_subject(topic=topic, subject=subject)

        self.assertEqual(storage_account_name, "ST_ACC_NAME")
        self.assertEqual(container_name, "CONTAINER_GUID")
        self.assertEqual(blob_name, "BLOB")

    def test_get_blob_info_from_url(self):
        url = "https://stalimextest.blob.core.windows.net/c144728c-3c69-4a58-afec-48c2ec8bfd45/test_dataset.txt"

        storage_account_name, container_name, blob_name = get_blob_info_from_blob_url(blob_url=url)

        self.assertEqual(storage_account_name, "stalimextest")
        self.assertEqual(container_name, "c144728c-3c69-4a58-afec-48c2ec8bfd45")
        self.assertEqual(blob_name, "test_dataset.txt")


    # TODO: fix this test
    # @patch('shared_code.blob_operations.get_blob_client_by_rg_and_account', return_value=Mock(BlobServiceClient))
    # def test_create_container_creates_container_with_valid_name(self, get_blob_client_by_rg_and_account_mock):
    #     request_id = "c4b39v99-6d96-4395-8e3b-bef891e3d6b4"

    #     storage_management_client = Mock(StorageManagementClient)
    #     storage_management_client.storage_accounts = Mock(StorageAccountsOperations)

    #     sa_keys_result = StorageAccountListKeysResult()
    #     key1 = StorageAccountKey()
    #     key1.key_name = "key1"
    #     key1.value = "accountKey1"

    #     sa_keys_result.keys = [key1]
    #     storage_management_client.storage_accounts.list_keys = MagicMock(return_value=sa_keys_result)

    #     blob_service_client_mock = get_blob_client_by_rg_and_account_mock("sa_rg_name", "sa_account_name",
    #                                                                       storage_management_client)
    #     create_container("sa_rg_name", "sa_account_name", request_id, storage_management_client)
    #     blob_service_client_mock.create_container.assert_called_with(request_id)
