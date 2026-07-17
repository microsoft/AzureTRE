import pytest
from unittest.mock import MagicMock, patch

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError, HttpResponseError

from shared_code.blob_operations_metadata import (
    get_account_url,
    get_storage_endpoint_suffix,
    create_container_with_metadata,
    update_container_stage,
    get_container_stage,
    get_container_metadata,
    get_request_files,
    delete_container_by_request_id
)


class TestGetAccountUrl:

    @patch.dict('os.environ', {"STORAGE_ENDPOINT_SUFFIX": "core.windows.net"}, clear=True)
    def test_returns_correct_url_format(self):
        url = get_account_url("mystorageaccount")
        assert url == "https://mystorageaccount.blob.core.windows.net/"

    @patch.dict('os.environ', {"STORAGE_ENDPOINT_SUFFIX": "core.chinacloudapi.cn"}, clear=True)
    def test_uses_custom_endpoint_suffix(self):
        url = get_account_url("mystorageaccount")
        assert url == "https://mystorageaccount.blob.core.chinacloudapi.cn/"

    @patch.dict('os.environ', {}, clear=True)
    def test_uses_default_endpoint_when_not_set(self):
        url = get_account_url("mystorageaccount")
        assert url == "https://mystorageaccount.blob.core.windows.net/"


class TestGetStorageEndpointSuffix:

    @patch.dict('os.environ', {"STORAGE_ENDPOINT_SUFFIX": "core.usgovcloudapi.net"}, clear=True)
    def test_returns_configured_suffix(self):
        suffix = get_storage_endpoint_suffix()
        assert suffix == "core.usgovcloudapi.net"

    @patch.dict('os.environ', {}, clear=True)
    def test_returns_default_when_not_configured(self):
        suffix = get_storage_endpoint_suffix()
        assert suffix == "core.windows.net"


class TestCreateContainerWithMetadata:

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_creates_container_with_stage_metadata(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        create_container_with_metadata(
            account_name="storageaccount",
            request_id="request-123",
            stage="import-external"
        )

        mock_container_client.create_container.assert_called_once()
        call_args = mock_container_client.create_container.call_args
        metadata = call_args.kwargs['metadata']

        assert metadata['stage'] == "import-external"
        assert 'created_at' in metadata
        assert 'last_stage_change' in metadata
        assert metadata['stage_history'] == "import-external"

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_creates_container_with_all_optional_metadata(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        create_container_with_metadata(
            account_name="storageaccount",
            request_id="request-123",
            stage="export-internal",
            workspace_id="ws-456",
            request_type="export",
            created_by="user@example.com"
        )

        call_args = mock_container_client.create_container.call_args
        metadata = call_args.kwargs['metadata']

        assert metadata['stage'] == "export-internal"
        assert metadata['workspace_id'] == "ws-456"
        assert metadata['request_type'] == "export"
        assert metadata['created_by'] == "user@example.com"

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_handles_container_already_exists(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_container_client.create_container.side_effect = ResourceExistsError("Container already exists")
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        create_container_with_metadata(
            account_name="storageaccount",
            request_id="request-123",
            stage="import-external"
        )


class TestUpdateContainerStage:

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_updates_stage_metadata(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_properties = MagicMock()
        mock_properties.metadata = {
            'stage': 'import-external',
            'stage_history': 'import-external',
            'created_at': '2024-01-01T00:00:00'
        }
        mock_container_client.get_container_properties.return_value = mock_properties
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        update_container_stage(
            account_name="storageaccount",
            request_id="request-123",
            new_stage="import-in-progress"
        )

        mock_container_client.set_container_metadata.assert_called_once()
        call_args = mock_container_client.set_container_metadata.call_args
        updated_metadata = call_args.args[0]

        assert updated_metadata['stage'] == "import-in-progress"
        assert "import-in-progress" in updated_metadata['stage_history']
        assert 'last_stage_change' in updated_metadata

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_appends_to_stage_history(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_properties = MagicMock()
        mock_properties.metadata = {
            'stage': 'import-external',
            'stage_history': 'import-external',
        }
        mock_container_client.get_container_properties.return_value = mock_properties
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        update_container_stage(
            account_name="storageaccount",
            request_id="request-123",
            new_stage="import-in-progress"
        )

        call_args = mock_container_client.set_container_metadata.call_args
        updated_metadata = call_args.args[0]

        assert updated_metadata['stage_history'] == "import-external,import-in-progress"

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_adds_changed_by_when_provided(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_properties = MagicMock()
        mock_properties.metadata = {'stage': 'import-external', 'stage_history': 'import-external'}
        mock_container_client.get_container_properties.return_value = mock_properties
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        update_container_stage(
            account_name="storageaccount",
            request_id="request-123",
            new_stage="import-in-progress",
            changed_by="processor"
        )

        call_args = mock_container_client.set_container_metadata.call_args
        updated_metadata = call_args.args[0]

        assert updated_metadata['last_changed_by'] == "processor"

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_adds_additional_metadata(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_properties = MagicMock()
        mock_properties.metadata = {'stage': 'import-in-progress', 'stage_history': 'import-external,import-in-progress'}
        mock_container_client.get_container_properties.return_value = mock_properties
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        update_container_stage(
            account_name="storageaccount",
            request_id="request-123",
            new_stage="import-approved",
            additional_metadata={"scan_result": "clean", "scan_time": "2024-01-01T12:00:00"}
        )

        call_args = mock_container_client.set_container_metadata.call_args
        updated_metadata = call_args.args[0]

        assert updated_metadata['scan_result'] == "clean"
        assert updated_metadata['scan_time'] == "2024-01-01T12:00:00"

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_raises_when_container_not_found(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_container_client.get_container_properties.side_effect = ResourceNotFoundError("Container not found")
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        with pytest.raises(ResourceNotFoundError):
            update_container_stage(
                account_name="storageaccount",
                request_id="nonexistent-request",
                new_stage="import-in-progress"
            )

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_raises_on_http_error(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_properties = MagicMock()
        mock_properties.metadata = {'stage': 'import-external'}
        mock_container_client.get_container_properties.return_value = mock_properties
        mock_container_client.set_container_metadata.side_effect = HttpResponseError("Service Error")
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        with pytest.raises(HttpResponseError):
            update_container_stage(
                account_name="storageaccount",
                request_id="request-123",
                new_stage="import-in-progress"
            )


class TestGetContainerStage:

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_returns_stage_from_metadata(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_properties = MagicMock()
        mock_properties.metadata = {'stage': 'import-in-progress'}
        mock_container_client.get_container_properties.return_value = mock_properties
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        stage = get_container_stage(
            account_name="storageaccount",
            request_id="request-123"
        )

        assert stage == "import-in-progress"

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_returns_unknown_when_stage_missing(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_properties = MagicMock()
        mock_properties.metadata = {}
        mock_container_client.get_container_properties.return_value = mock_properties
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        stage = get_container_stage(
            account_name="storageaccount",
            request_id="request-123"
        )

        assert stage == "unknown"

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_raises_when_container_not_found(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_container_client.get_container_properties.side_effect = ResourceNotFoundError("Container not found")
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        with pytest.raises(ResourceNotFoundError):
            get_container_stage(
                account_name="storageaccount",
                request_id="nonexistent-request"
            )


class TestGetContainerMetadata:

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_returns_all_metadata(self, mock_get_credential, mock_blob_service_client):
        expected_metadata = {
            'stage': 'import-in-progress',
            'workspace_id': 'ws-123',
            'request_type': 'import',
            'created_at': '2024-01-01T00:00:00',
            'stage_history': 'import-external,import-in-progress'
        }

        mock_container_client = MagicMock()
        mock_properties = MagicMock()
        mock_properties.metadata = expected_metadata
        mock_container_client.get_container_properties.return_value = mock_properties
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        metadata = get_container_metadata(
            account_name="storageaccount",
            request_id="request-123"
        )

        assert metadata == expected_metadata

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_raises_when_container_not_found(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_container_client.get_container_properties.side_effect = ResourceNotFoundError("Container not found")
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        with pytest.raises(ResourceNotFoundError):
            get_container_metadata(
                account_name="storageaccount",
                request_id="nonexistent-request"
            )


class TestGetRequestFiles:

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_returns_list_of_files(self, mock_get_credential, mock_blob_service_client):
        mock_blob1 = MagicMock()
        mock_blob1.name = "data.csv"
        mock_blob1.size = 1024

        mock_blob2 = MagicMock()
        mock_blob2.name = "readme.txt"
        mock_blob2.size = 256

        mock_container_client = MagicMock()
        mock_container_client.list_blobs.return_value = [mock_blob1, mock_blob2]
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        files = get_request_files(
            account_name="storageaccount",
            request_id="request-123"
        )

        assert len(files) == 2
        assert files[0] == {"name": "data.csv", "size": 1024}
        assert files[1] == {"name": "readme.txt", "size": 256}

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_returns_empty_list_when_no_files(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_container_client.list_blobs.return_value = []
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        files = get_request_files(
            account_name="storageaccount",
            request_id="request-123"
        )

        assert files == []


class TestDeleteContainerByRequestId:

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_deletes_container(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        delete_container_by_request_id(
            account_name="storageaccount",
            request_id="request-123"
        )

        mock_container_client.delete_container.assert_called_once()

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_handles_container_not_found(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_container_client.delete_container.side_effect = ResourceNotFoundError("Container not found")
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        delete_container_by_request_id(
            account_name="storageaccount",
            request_id="nonexistent-request"
        )

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_raises_on_http_error(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_container_client.delete_container.side_effect = HttpResponseError("Service Error")
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        with pytest.raises(HttpResponseError):
            delete_container_by_request_id(
                account_name="storageaccount",
                request_id="request-123"
            )


class TestStageTransitions:

    ABAC_ALLOWED_STAGES = ['import-external', 'import-in-progress', 'export-approved']

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_import_stage_transition_updates_history(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()

        current_metadata = {
            'stage': 'import-external',
            'stage_history': 'import-external'
        }
        mock_properties = MagicMock()
        mock_properties.metadata = current_metadata.copy()
        mock_container_client.get_container_properties.return_value = mock_properties
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        update_container_stage(
            account_name="storageaccount",
            request_id="request-123",
            new_stage="import-in-progress"
        )

        call_args = mock_container_client.set_container_metadata.call_args
        updated_metadata = call_args.args[0]

        assert updated_metadata['stage'] == "import-in-progress"
        assert updated_metadata['stage_history'] == "import-external,import-in-progress"

    @patch("shared_code.blob_operations_metadata.BlobServiceClient")
    @patch("shared_code.blob_operations_metadata.get_credential")
    def test_scan_result_metadata_added_on_approval(self, mock_get_credential, mock_blob_service_client):
        mock_container_client = MagicMock()
        mock_properties = MagicMock()
        mock_properties.metadata = {
            'stage': 'import-in-progress',
            'stage_history': 'import-external,import-in-progress'
        }
        mock_container_client.get_container_properties.return_value = mock_properties
        mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client

        update_container_stage(
            account_name="storageaccount",
            request_id="request-123",
            new_stage="import-approved",
            additional_metadata={
                "scan_result": "clean",
                "scan_completed_at": "2024-01-01T12:00:00Z"
            }
        )

        call_args = mock_container_client.set_container_metadata.call_args
        updated_metadata = call_args.args[0]

        assert updated_metadata['stage'] == "import-approved"
        assert updated_metadata['scan_result'] == "clean"
        assert "import-approved" not in self.ABAC_ALLOWED_STAGES
