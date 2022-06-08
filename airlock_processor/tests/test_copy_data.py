from json import JSONDecodeError
import unittest

from StatusChangedQueueTrigger import extract_properties, get_source_dest_env_vars, is_require_data_copy


class TestPropertiesExtraction(unittest.TestCase):
    def test_extract_prop_valid_body_return_all_values(self):
        msg = "{ \"request_id\":\"123\",\"new_status\":\"456\" , \"type\":\"789\", \"workspace_id\":\"ws1\", \"tre_id\":\"123\"  }"
        req_id, req_status, req_type, tre_id, ws_id = extract_properties(msg)
        self.assertEqual(req_id, "123")
        self.assertEqual(req_status, "456")
        self.assertEqual(req_type, "789")
        self.assertEqual(tre_id, "123")
        self.assertEqual(ws_id, "ws1")

        msg = "{ \"new_status\":\"456\" , \"type\":\"789\"  }"
        self.assertRaises(KeyError, extract_properties, msg)

        msg = "{ \"request_id\":\"123\", \"type\":\"789\"  }"
        self.assertRaises(KeyError, extract_properties, msg)

        msg = "{ \"request_id\":\"123\",\"new_status\":\"456\" }"
        self.assertRaises(KeyError, extract_properties, msg)

    def test_extract_prop_missing_arg_throws(self):
        msg = "{ \"new_status\":\"456\" , \"type\":\"789\"  }"
        self.assertRaises(KeyError, extract_properties, msg)

        msg = "{ \"request_id\":\"123\", \"type\":\"789\"  }"
        self.assertRaises(KeyError, extract_properties, msg)

        msg = "{ \"request_id\":\"123\",\"new_status\":\"456\" }"
        self.assertRaises(KeyError, extract_properties, msg)

    def test_extract_prop_invalid_json_throws(self):
        msg = "Hi"
        self.assertRaises(JSONDecodeError, extract_properties, msg)


class TestDataCopyProperties(unittest.TestCase):
    def test_only_specific_status_are_triggering_copy(self):
        self.assertEqual(is_require_data_copy("Mitzi"), False)
        self.assertEqual(is_require_data_copy(""), False)
        self.assertEqual(is_require_data_copy("submit"), False)

        # Testing all values that should return true
        self.assertEqual(is_require_data_copy("submITted"), True)
        self.assertEqual(is_require_data_copy("submitted"), True)
        self.assertEqual(is_require_data_copy("approved"), True)
        self.assertEqual(is_require_data_copy("REJected"), True)
        self.assertEqual(is_require_data_copy("blocked"), True)

    def test_wrong_status_raises_when_getting_storage_account_properties(self):
        self.assertRaises(Exception, get_source_dest_env_vars, "Miaow", "import")

    def test_wrong_type_raises_when_getting_storage_account_properties(self):
        self.assertRaises(Exception, get_source_dest_env_vars, "accepted", "somethingelse")
