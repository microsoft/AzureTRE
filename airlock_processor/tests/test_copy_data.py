from json import JSONDecodeError
import unittest

from pydantic import ValidationError
from StatusChangedQueueTrigger import extract_properties, get_source_dest_for_copy, is_require_data_copy
from azure.functions.servicebus import ServiceBusMessage


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


def _mock_service_bus_message(body: str):
    encoded_body = str.encode(body, "utf-8")
    message = ServiceBusMessage(body=encoded_body, message_id="123", user_properties={})
    return message
