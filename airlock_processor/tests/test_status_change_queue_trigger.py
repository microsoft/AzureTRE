from json import JSONDecodeError
import os
import pytest
from mock import MagicMock, patch

from pydantic import ValidationError
from StatusChangedQueueTrigger import get_request_files, main, extract_properties, get_source_dest_for_copy, is_require_data_copy
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


def _mock_service_bus_message(body: str):
    encoded_body = str.encode(body, "utf-8")
    message = ServiceBusMessage(body=encoded_body, message_id="123", user_properties={})
    return message
