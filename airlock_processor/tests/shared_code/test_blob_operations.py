import unittest


from shared_code.blob_operations import get_blob_info_from_topic_and_subject, get_blob_info_from_blob_url


class TestBlobOperations(unittest.TestCase):
    def test_get_blob_info_from_topic_and_subject(self):
        topic = "/subscriptions/SUB_ID/resourceGroups/RG_NAME/providers/Microsoft.Storage/storageAccounts/ST_ACC_NAME"
        subject = "/blobServices/default/containers/c144728c-3c69-4a58-afec-48c2ec8bfd45/blobs/BLOB"

        storage_account_name, container_name, blob_name = get_blob_info_from_topic_and_subject(topic=topic, subject=subject)

        self.assertEqual(storage_account_name, "ST_ACC_NAME")
        self.assertEqual(container_name, "c144728c-3c69-4a58-afec-48c2ec8bfd45")
        self.assertEqual(blob_name, "BLOB")

    def test_get_blob_info_from_url(self):
        url = "https://stalimextest.blob.core.windows.net/c144728c-3c69-4a58-afec-48c2ec8bfd45/test_dataset.txt"

        storage_account_name, container_name, blob_name = get_blob_info_from_blob_url(blob_url=url)

        self.assertEqual(storage_account_name, "stalimextest")
        self.assertEqual(container_name, "c144728c-3c69-4a58-afec-48c2ec8bfd45")
        self.assertEqual(blob_name, "test_dataset.txt")

    # TODO: write a test for copy data
    def test_copy_data(self):
        pass
