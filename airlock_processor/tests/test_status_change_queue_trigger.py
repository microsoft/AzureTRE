from json import JSONDecodeError
import os
import unittest
from unittest import mock
from unittest.mock import MagicMock, patch

from pydantic import ValidationError
from StatusChangedQueueTrigger import get_request_files, main, extract_properties, get_source_dest_for_copy, is_require_data_copy
from azure.functions.servicebus import ServiceBusMessage
from shared_code import constants


class TestPropertiesExtraction(unittest.TestCase):
    def test_extract_prop_valid_body_return_all_values(self):
        message_body = "{ \"data\": { \"request_id\":\"123\",\"status\":\"456\" , \"type\":\"789\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        req_prop = extract_properties(message)
        self.assertEqual(req_prop.request_id, "123")
        self.assertEqual(req_prop.status, "456")
        self.assertEqual(req_prop.type, "789")
        self.assertEqual(req_prop.workspace_id, "ws1")

    def test_extract_prop_missing_arg_throws(self):
        message_body = "{ \"data\": { \"status\":\"456\" , \"type\":\"789\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        self.assertRaises(ValidationError, extract_properties, message)

        message_body = "{ \"data\": { \"request_id\":\"123\", \"type\":\"789\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        self.assertRaises(ValidationError, extract_properties, message)

        message_body = "{ \"data\": { \"request_id\":\"123\",\"status\":\"456\" ,  \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        self.assertRaises(ValidationError, extract_properties, message)

        message_body = "{ \"data\": { \"request_id\":\"123\",\"status\":\"456\" , \"type\":\"789\"  }}"
        message = _mock_service_bus_message(body=message_body)
        self.assertRaises(ValidationError, extract_properties, message)

    def test_extract_prop_invalid_json_throws(self):
        message_body = "Hi"
        message = _mock_service_bus_message(body=message_body)
        self.assertRaises(JSONDecodeError, extract_properties, message)


class TestDataCopyProperties(unittest.TestCase):
    def test_only_specific_status_are_triggering_copy(self):
        self.assertEqual(is_require_data_copy("Mitzi"), False)
        self.assertEqual(is_require_data_copy(""), False)
        self.assertEqual(is_require_data_copy("submit"), False)
        self.assertEqual(is_require_data_copy("approved"), False)
        self.assertEqual(is_require_data_copy("REJected"), False)
        self.assertEqual(is_require_data_copy("blocked"), False)

        # Testing all values that should return true
        self.assertEqual(is_require_data_copy("submITted"), True)
        self.assertEqual(is_require_data_copy("submitted"), True)
        self.assertEqual(is_require_data_copy("approval_in_progress"), True)
        self.assertEqual(is_require_data_copy("rejection_in_progress"), True)
        self.assertEqual(is_require_data_copy("blocking_in_progress"), True)

    def test_wrong_status_raises_when_getting_storage_account_properties(self):
        self.assertRaises(Exception, get_source_dest_for_copy, "Miaow", "import")

    def test_wrong_type_raises_when_getting_storage_account_properties(self):
        self.assertRaises(Exception, get_source_dest_for_copy, "accepted", "somethingelse")


class TestFileEnumeration(unittest.TestCase):
    @patch("StatusChangedQueueTrigger.set_output_event_to_report_request_files")
    @patch("StatusChangedQueueTrigger.get_request_files")
    @patch("StatusChangedQueueTrigger.is_require_data_copy", return_value=False)
    @mock.patch.dict(os.environ, {"TRE_ID": "tre-id"}, clear=True)
    def test_get_request_files_should_be_called_on_submit_stage(self, _, mock_get_request_files, mock_set_output_event_to_report_request_files):
        message_body = "{ \"data\": { \"request_id\":\"123\",\"status\":\"submitted\" , \"type\":\"import\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        main(msg=message, outputEvent=MagicMock())
        self.assertTrue(mock_get_request_files.called)
        self.assertTrue(mock_set_output_event_to_report_request_files.called)

    @patch("StatusChangedQueueTrigger.set_output_event_to_report_failure")
    @patch("StatusChangedQueueTrigger.get_request_files")
    @patch("StatusChangedQueueTrigger.handle_status_changed")
    def test_get_request_files_should_not_be_called_if_new_status_is_not_submit(self, _, mock_get_request_files, mock_set_output_event_to_report_failure):
        message_body = "{ \"data\": { \"request_id\":\"123\",\"status\":\"fake-status\" , \"type\":\"import\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        main(msg=message, outputEvent=MagicMock())
        self.assertFalse(mock_get_request_files.called)
        self.assertFalse(mock_set_output_event_to_report_failure.called)

    @patch("StatusChangedQueueTrigger.set_output_event_to_report_failure")
    @patch("StatusChangedQueueTrigger.get_request_files")
    @patch("StatusChangedQueueTrigger.handle_status_changed", side_effect=Exception)
    def test_get_request_files_should_be_called_when_failing_during_submit_stage(self, _, mock_get_request_files, mock_set_output_event_to_report_failure):
        message_body = "{ \"data\": { \"request_id\":\"123\",\"status\":\"submitted\" , \"type\":\"import\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        main(msg=message, outputEvent=MagicMock())
        self.assertTrue(mock_get_request_files.called)
        self.assertTrue(mock_set_output_event_to_report_failure.called)

    @patch("StatusChangedQueueTrigger.blob_operations.get_request_files")
    @mock.patch.dict(os.environ, {"TRE_ID": "tre-id"}, clear=True)
    def test_get_request_files_called_with_correct_storage_account(self, mock_get_request_files):
        source_storage_account_for_submitted_stage = constants.STORAGE_ACCOUNT_NAME_EXPORT_INTERNAL + 'ws1'
        message_body = "{ \"data\": { \"request_id\":\"123\",\"status\":\"submitted\" , \"type\":\"export\", \"workspace_id\":\"ws1\"  }}"
        message = _mock_service_bus_message(body=message_body)
        request_properties = extract_properties(message)
        get_request_files(request_properties)
        mock_get_request_files.assert_called_with(account_name=source_storage_account_for_submitted_stage, request_id=request_properties.request_id)


def _mock_service_bus_message(body: str):
    encoded_body = str.encode(body, "utf-8")
    message = ServiceBusMessage(body=encoded_body, message_id="123", user_properties={})
    return message
