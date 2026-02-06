from json import JSONDecodeError
import os
import pytest
from mock import MagicMock, patch

from pydantic import ValidationError
from StatusChangedQueueTrigger import get_request_files, main, extract_properties, get_source_dest_for_copy, is_require_data_copy, get_storage_account_destination_for_copy, handle_status_changed
from azure.functions.servicebus import ServiceBusMessage
from shared_code import constants


class TestPropertiesExtraction():
    def test_extract_prop_valid_body_return_all_values(self):
        message_body = "{ \"data\": { \"request_id\":\"123\",\"new_status\":\"456\" ,\"previous_status\":\"789\" , \"type\":\"101112\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        req_prop = extract_properties(message)
        assert req_prop.request_id == "123"
        assert req_prop.new_status == "456"
        assert req_prop.previous_status == "789"
        assert req_prop.type == "101112"
        assert req_prop.workspace_id == "ws1"

    def test_extract_prop_with_review_workspace_id(self):
        message_body = "{ \"data\": { \"request_id\":\"123\",\"new_status\":\"456\" ,\"previous_status\":\"789\" , \"type\":\"101112\", \"workspace_id\":\"ws1\", \"review_workspace_id\":\"rw01\"  }}"
        message = _mock_service_bus_message(body=message_body)
        req_prop = extract_properties(message)
        assert req_prop.review_workspace_id == "rw01"

    def test_extract_prop_without_review_workspace_id_defaults_to_none(self):
        message_body = "{ \"data\": { \"request_id\":\"123\",\"new_status\":\"456\" ,\"previous_status\":\"789\" , \"type\":\"101112\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        req_prop = extract_properties(message)
        assert req_prop.review_workspace_id is None

    def test_extract_prop_missing_arg_throws(self):
        message_body = "{ \"data\": { \"status\":\"456\" , \"type\":\"789\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        pytest.raises(ValidationError, extract_properties, message)

        message_body = "{ \"data\": { \"request_id\":\"123\", \"type\":\"789\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        pytest.raises(ValidationError, extract_properties, message)

        message_body = "{ \"data\": { \"request_id\":\"123\",\"status\":\"456\" ,  \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        pytest.raises(ValidationError, extract_properties, message)

        message_body = "{ \"data\": { \"request_id\":\"123\",\"status\":\"456\" , \"type\":\"789\"  }}"
        message = _mock_service_bus_message(body=message_body)
        pytest.raises(ValidationError, extract_properties, message)

    def test_extract_prop_invalid_json_throws(self):
        message_body = "Hi"
        message = _mock_service_bus_message(body=message_body)
        pytest.raises(JSONDecodeError, extract_properties, message)


class TestDataCopyProperties():
    def test_only_specific_status_are_triggering_copy(self):
        assert not is_require_data_copy("Mitzi")
        assert not is_require_data_copy("")
        assert not is_require_data_copy("submit")
        assert not is_require_data_copy("approved")
        assert not is_require_data_copy("REJected")
        assert not is_require_data_copy("blocked")

        # Testing all values that should return true
        assert is_require_data_copy("submITted")
        assert is_require_data_copy("submitted")
        assert is_require_data_copy("approval_in_progress")
        assert is_require_data_copy("rejection_in_progress")
        assert is_require_data_copy("blocking_in_progress")

    def test_wrong_status_raises_when_getting_storage_account_properties(self):
        pytest.raises(Exception, get_source_dest_for_copy, "Miaow", "import")

    def test_wrong_type_raises_when_getting_storage_account_properties(self):
        pytest.raises(Exception, get_source_dest_for_copy, "accepted", "somethingelse")


class TestFileEnumeration():
    @patch("StatusChangedQueueTrigger.set_output_event_to_report_request_files")
    @patch("StatusChangedQueueTrigger.get_request_files")
    @patch("StatusChangedQueueTrigger.is_require_data_copy", return_value=False)
    @patch.dict(os.environ, {"TRE_ID": "tre-id"}, clear=True)
    def test_get_request_files_should_be_called_on_submit_stage(self, _, mock_get_request_files, mock_set_output_event_to_report_request_files):
        message_body = "{ \"data\": { \"request_id\":\"123\",\"new_status\":\"submitted\" ,\"previous_status\":\"draft\" , \"type\":\"export\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        main(msg=message, stepResultEvent=MagicMock(), dataDeletionEvent=MagicMock())
        assert mock_get_request_files.called
        assert mock_set_output_event_to_report_request_files.called

    @patch("StatusChangedQueueTrigger.set_output_event_to_report_failure")
    @patch("StatusChangedQueueTrigger.get_request_files")
    @patch("StatusChangedQueueTrigger.handle_status_changed")
    def test_get_request_files_should_not_be_called_if_new_status_is_not_submit(self, _, mock_get_request_files, mock_set_output_event_to_report_failure):
        message_body = "{ \"data\": { \"request_id\":\"123\",\"new_status\":\"fake-status\" ,\"previous_status\":\"None\" , \"type\":\"export\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        main(msg=message, stepResultEvent=MagicMock(), dataDeletionEvent=MagicMock())
        assert not mock_get_request_files.called
        assert not mock_set_output_event_to_report_failure.called

    @patch("StatusChangedQueueTrigger.set_output_event_to_report_failure")
    @patch("StatusChangedQueueTrigger.get_request_files")
    @patch("StatusChangedQueueTrigger.handle_status_changed", side_effect=Exception)
    def test_get_request_files_should_be_called_when_failing_during_submit_stage(self, _, mock_get_request_files, mock_set_output_event_to_report_failure):
        message_body = "{ \"data\": { \"request_id\":\"123\",\"new_status\":\"submitted\" ,\"previous_status\":\"draft\" , \"type\":\"export\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        main(msg=message, stepResultEvent=MagicMock(), dataDeletionEvent=MagicMock())
        assert mock_get_request_files.called
        assert mock_set_output_event_to_report_failure.called

    @patch("StatusChangedQueueTrigger.blob_operations.get_request_files")
    @patch.dict(os.environ, {"TRE_ID": "tre-id"}, clear=True)
    def test_get_request_files_called_with_correct_storage_account(self, mock_get_request_files):
        source_storage_account_for_submitted_stage = constants.STORAGE_ACCOUNT_NAME_EXPORT_INTERNAL + 'ws1'
        message_body = "{ \"data\": { \"request_id\":\"123\",\"new_status\":\"submitted\" ,\"previous_status\":\"draft\" , \"type\":\"export\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        request_properties = extract_properties(message)
        get_request_files(request_properties)
        mock_get_request_files.assert_called_with(account_name=source_storage_account_for_submitted_stage, request_id=request_properties.request_id)


class TestFilesDeletion():
    @patch("StatusChangedQueueTrigger.set_output_event_to_trigger_container_deletion")
    @patch.dict(os.environ, {"TRE_ID": "tre-id"}, clear=True)
    def test_delete_request_files_should_be_called_on_cancel_stage(self, mock_set_output_event_to_trigger_container_deletion):
        message_body = "{ \"data\": { \"request_id\":\"123\",\"new_status\":\"cancelled\" ,\"previous_status\":\"draft\" , \"type\":\"export\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        main(msg=message, stepResultEvent=MagicMock(), dataDeletionEvent=MagicMock())
        assert mock_set_output_event_to_trigger_container_deletion.called


class TestImportSubmitUsesReviewWorkspaceId():
    @patch.dict(os.environ, {"TRE_ID": "tre-id"}, clear=True)
    def test_import_submit_destination_uses_review_workspace_id(self):
        dest = get_storage_account_destination_for_copy(
            new_status=constants.STAGE_SUBMITTED,
            request_type=constants.IMPORT_TYPE,
            short_workspace_id="ws01",
            review_workspace_id="rw01"
        )
        assert dest == constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS + "rw01"

    @patch.dict(os.environ, {"TRE_ID": "tre-id"}, clear=True)
    def test_import_submit_destination_falls_back_to_workspace_id_when_no_review_workspace_id(self):
        dest = get_storage_account_destination_for_copy(
            new_status=constants.STAGE_SUBMITTED,
            request_type=constants.IMPORT_TYPE,
            short_workspace_id="ws01",
            review_workspace_id=None
        )
        assert dest == constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS + "ws01"

    @patch.dict(os.environ, {"TRE_ID": "tre-id"}, clear=True)
    def test_export_submit_destination_ignores_review_workspace_id(self):
        dest = get_storage_account_destination_for_copy(
            new_status=constants.STAGE_SUBMITTED,
            request_type=constants.EXPORT_TYPE,
            short_workspace_id="ws01",
            review_workspace_id="rw01"
        )
        assert dest == constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS + "ws01"


class TestImportApprovalMetadataOnly():
    @patch("StatusChangedQueueTrigger.blob_operations.copy_data")
    @patch("StatusChangedQueueTrigger.blob_operations.create_container")
    @patch.dict(os.environ, {"TRE_ID": "tre-id"}, clear=True)
    def test_import_approval_does_not_copy_data(self, mock_create_container, mock_copy_data):
        message_body = "{ \"data\": { \"request_id\":\"123\",\"new_status\":\"approval_in_progress\" ,\"previous_status\":\"in_review\" , \"type\":\"import\", \"workspace_id\":\"ws01\"  }}"
        message = _mock_service_bus_message(body=message_body)
        main(msg=message, stepResultEvent=MagicMock(), dataDeletionEvent=MagicMock())
        mock_create_container.assert_called_once()
        mock_copy_data.assert_not_called()


def _mock_service_bus_message(body: str):
    encoded_body = str.encode(body, "utf-8")
    message = ServiceBusMessage(body=encoded_body, message_id="123", user_properties={}, application_properties={})
    return message
