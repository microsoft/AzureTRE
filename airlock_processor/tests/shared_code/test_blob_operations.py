from collections import namedtuple
import json
import pytest
from mock import MagicMock, patch

from shared_code.blob_operations import get_blob_info_from_topic_and_subject, get_blob_info_from_blob_url, copy_data, get_blob_url, get_storage_endpoint_suffix, is_submission_sealed
from exceptions import TooManyFilesInRequestException, NoFilesInRequestException


def get_test_blob():
    return namedtuple("Blob", "name")


class TestBlobOperations():

    def test_get_blob_info_from_topic_and_subject(self):
        topic = "/subscriptions/SUB_ID/resourceGroups/RG_NAME/providers/Microsoft.Storage/storageAccounts/ST_ACC_NAME"
        subject = "/blobServices/default/containers/c144728c-3c69-4a58-afec-48c2ec8bfd45/blobs/BLOB"

        storage_account_name, container_name, blob_name = get_blob_info_from_topic_and_subject(topic=topic, subject=subject)

        assert storage_account_name == "ST_ACC_NAME"
        assert container_name == "c144728c-3c69-4a58-afec-48c2ec8bfd45"
        assert blob_name == "BLOB"

    def test_get_blob_info_from_url(self):
        url = f"https://stalimextest.blob.{get_storage_endpoint_suffix()}/c144728c-3c69-4a58-afec-48c2ec8bfd45/test_dataset.txt"

        storage_account_name, container_name, blob_name = get_blob_info_from_blob_url(blob_url=url)

        assert storage_account_name == "stalimextest"
        assert container_name == "c144728c-3c69-4a58-afec-48c2ec8bfd45"
        assert blob_name == "test_dataset.txt"

    @patch("shared_code.blob_operations.BlobServiceClient")
    def test_copy_data_fails_if_too_many_blobs_to_copy(self, mock_blob_service_client):
        mock_blob_service_client().get_container_client().list_blobs = MagicMock(return_value=[get_test_blob()("a"), get_test_blob()("b")])

        with pytest.raises(TooManyFilesInRequestException):
            copy_data("source_acc", "dest_acc", "req_id")

    @patch("shared_code.blob_operations.BlobServiceClient")
    def test_copy_data_fails_if_no_blobs_to_copy(self, mock_blob_service_client):
        mock_blob_service_client().get_container_client().list_blobs = MagicMock(return_value=[])

        with pytest.raises(NoFilesInRequestException):
            copy_data("source_acc", "dest_acc", "req_id")

    @patch("shared_code.blob_operations.BlobServiceClient")
    @patch("shared_code.blob_operations.generate_container_sas", return_value="sas")
    def test_copy_data_adds_copied_from_metadata(self, _, mock_blob_service_client):
        source_url = f"http://storageacct.blob.{get_storage_endpoint_suffix()}/container/blob"

        # Check for two scenarios: when there's no copied_from history in metadata, and when there is some
        for source_metadata, dest_metadata in [
            ({"a": "b"}, {"a": "b", "copied_from": json.dumps([source_url])}),
            ({"a": "b", "copied_from": json.dumps(["old_url"])}, {"a": "b", "copied_from": json.dumps(["old_url", source_url])})
        ]:
            source_blob_client_mock = MagicMock()
            source_blob_client_mock.url = source_url
            source_blob_client_mock.get_blob_properties = MagicMock(return_value={"metadata": source_metadata})

            dest_blob_client_mock = MagicMock()
            dest_blob_client_mock.bla = "bla"
            dest_blob_client_mock.start_copy_from_url = MagicMock(return_value={"copy_id": "123", "copy_status": "success"})

            # Set source blob mock
            mock_blob_service_client().get_container_client().get_blob_client = MagicMock(return_value=source_blob_client_mock)
            # Set dest blob mock
            mock_blob_service_client().get_blob_client = MagicMock(return_value=dest_blob_client_mock)

            # Any additional mocks for the copy_data method to work
            mock_blob_service_client().get_user_delegation_key = MagicMock(return_value="key")
            mock_blob_service_client().get_container_client().list_blobs = MagicMock(return_value=[get_test_blob()("a")])

            copy_data("source_acc", "dest_acc", "req_id")

            # Check that copied_from field was set correctly in the metadata
            dest_blob_client_mock.start_copy_from_url.assert_called_with(f"{source_url}?sas", metadata=dest_metadata)

    @patch("shared_code.blob_operations.BlobServiceClient")
    @patch("shared_code.blob_operations.generate_container_sas", return_value="sas")
    def test_copy_data_adds_submission_sealed_metadata(self, _, mock_blob_service_client):
        source_blob_client_mock = MagicMock()
        source_blob_client_mock.url = "http://storageacct/container/blob"
        source_blob_client_mock.get_blob_properties.return_value = {"metadata": {}}
        dest_blob_client_mock = MagicMock()
        dest_blob_client_mock.start_copy_from_url.return_value = {"copy_id": "123", "copy_status": "success"}
        mock_blob_service_client().get_container_client().get_blob_client.return_value = source_blob_client_mock
        mock_blob_service_client().get_blob_client.return_value = dest_blob_client_mock
        mock_blob_service_client().get_container_client().list_blobs.return_value = [get_test_blob()("a")]

        copy_data("source_acc", "dest_acc", "req_id", additional_metadata={"submission_sealed": "true"})

        metadata = dest_blob_client_mock.start_copy_from_url.call_args.kwargs["metadata"]
        assert metadata["submission_sealed"] == "true"

    @patch("shared_code.blob_operations.BlobServiceClient")
    def test_is_submission_sealed_requires_marker_and_successful_copy(self, mock_blob_service_client):
        container_client = mock_blob_service_client().get_container_client.return_value
        container_client.list_blobs.return_value = [get_test_blob()("blob")]
        properties = MagicMock()
        properties.metadata = {"submission_sealed": "true"}
        properties.copy.status = "success"
        container_client.get_blob_client.return_value.get_blob_properties.return_value = properties

        assert is_submission_sealed("account", "request") is True

    @patch("shared_code.blob_operations.time.sleep")
    @patch("shared_code.blob_operations.BlobServiceClient")
    @patch("shared_code.blob_operations.generate_container_sas", return_value="sas")
    def test_copy_data_waits_for_pending_copy(self, _, mock_blob_service_client, __):
        # The caller deletes the source immediately afterwards, so returning while the copy is
        # still pending would abort it and lose the data.
        source_url = f"http://storageacct.blob.{get_storage_endpoint_suffix()}/container/blob"
        source_blob_client_mock = MagicMock()
        source_blob_client_mock.url = source_url
        source_blob_client_mock.get_blob_properties = MagicMock(return_value={"metadata": {}})

        dest_blob_client_mock = MagicMock()
        dest_blob_client_mock.start_copy_from_url = MagicMock(return_value={"copy_id": "123", "copy_status": "pending"})
        dest_blob_client_mock.get_blob_properties = MagicMock(side_effect=[
            MagicMock(copy=MagicMock(status="pending")),
            MagicMock(copy=MagicMock(status="success"))])

        mock_blob_service_client().get_container_client().get_blob_client = MagicMock(return_value=source_blob_client_mock)
        mock_blob_service_client().get_blob_client = MagicMock(return_value=dest_blob_client_mock)
        mock_blob_service_client().get_user_delegation_key = MagicMock(return_value="key")
        mock_blob_service_client().get_container_client().list_blobs = MagicMock(return_value=[get_test_blob()("a")])

        copy_data("source_acc", "dest_acc", "req_id")

        assert dest_blob_client_mock.get_blob_properties.call_count == 2

    @patch("shared_code.blob_operations.time.sleep")
    @patch("shared_code.blob_operations.BlobServiceClient")
    @patch("shared_code.blob_operations.generate_container_sas", return_value="sas")
    def test_copy_data_raises_if_copy_never_succeeds(self, _, mock_blob_service_client, __):
        source_url = f"http://storageacct.blob.{get_storage_endpoint_suffix()}/container/blob"
        source_blob_client_mock = MagicMock()
        source_blob_client_mock.url = source_url
        source_blob_client_mock.get_blob_properties = MagicMock(return_value={"metadata": {}})

        dest_blob_client_mock = MagicMock()
        dest_blob_client_mock.start_copy_from_url = MagicMock(return_value={"copy_id": "123", "copy_status": "failed"})

        mock_blob_service_client().get_container_client().get_blob_client = MagicMock(return_value=source_blob_client_mock)
        mock_blob_service_client().get_blob_client = MagicMock(return_value=dest_blob_client_mock)
        mock_blob_service_client().get_user_delegation_key = MagicMock(return_value="key")
        mock_blob_service_client().get_container_client().list_blobs = MagicMock(return_value=[get_test_blob()("a")])

        with pytest.raises(Exception, match="did not complete"):
            copy_data("source_acc", "dest_acc", "req_id")

    @patch("shared_code.blob_operations.time.sleep")
    @patch("shared_code.blob_operations.BlobServiceClient")
    @patch("shared_code.blob_operations.generate_container_sas", return_value="sas")
    def test_copy_data_aborts_a_copy_still_pending_at_timeout(self, _, mock_blob_service_client, __):
        # A late completion after we have failed the request would recreate the destination and orphan data.
        source_url = f"http://storageacct.blob.{get_storage_endpoint_suffix()}/container/blob"
        source_blob_client_mock = MagicMock()
        source_blob_client_mock.url = source_url
        source_blob_client_mock.get_blob_properties = MagicMock(return_value={"metadata": {}})

        dest_blob_client_mock = MagicMock()
        dest_blob_client_mock.start_copy_from_url = MagicMock(return_value={"copy_id": "123", "copy_status": "pending"})
        dest_blob_client_mock.get_blob_properties = MagicMock(return_value=MagicMock(copy=MagicMock(status="pending")))

        mock_blob_service_client().get_container_client().get_blob_client = MagicMock(return_value=source_blob_client_mock)
        mock_blob_service_client().get_blob_client = MagicMock(return_value=dest_blob_client_mock)
        mock_blob_service_client().get_user_delegation_key = MagicMock(return_value="key")
        mock_blob_service_client().get_container_client().list_blobs = MagicMock(return_value=[get_test_blob()("a")])

        with pytest.raises(Exception, match="did not complete"):
            copy_data("source_acc", "dest_acc", "req_id")
        dest_blob_client_mock.abort_copy.assert_called_once_with("123")

        account_name = "account"
        container_name = "container"
        blob_name = "blob"

        blob_url = get_blob_url(account_name, container_name, blob_name)
        assert blob_url == f"https://{account_name}.blob.{get_storage_endpoint_suffix()}/{container_name}/{blob_name}"

    def test_get_blob_url_without_blob_name_should_return_container_url(self):
        account_name = "account"
        container_name = "container"

        blob_url = get_blob_url(account_name, container_name)
        assert blob_url == f"https://{account_name}.blob.{get_storage_endpoint_suffix()}/{container_name}/"
