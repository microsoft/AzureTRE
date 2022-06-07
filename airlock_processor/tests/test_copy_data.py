from json import JSONDecodeError
import os
import unittest
from unittest import mock

from StatusChangedQueueTrigger import extract_properties, get_source_dest_env_vars, is_require_data_copy


class TestPropertiesExtraction(unittest.TestCase):
    def test_extract_prop_valid_body_return_all_values(self):
        msg = "{ \"request_id\":\"123\",\"new_status\":\"456\" , \"type\":\"789\"  }"
        req_id, req_status, req_type = extract_properties(msg)
        self.assertEqual(req_id, "123")
        self.assertEqual(req_status, "456")
        self.assertEqual(req_type, "789")

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

    @mock.patch.dict(os.environ, {"AZURE_STORAGE_ACCOUNT_NAME_STRING_IMPORT_EXTERNAL": "1_1"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_ACCOUNT_KEY_STRING_IMPORT_EXTERNAL": "1_2"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING_IMPORT_EXTERNAL": "1_3"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING_IMPORT_INPROGRESS": "1_4_3_3_5_3"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_ACCOUNT_NAME_STRING_EXPORT_INTERNAL": "2_1"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_ACCOUNT_KEY_STRING_EXPORT_INTERNAL": "2_2"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING_EXPORT_INTERNAL": "2_3"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING_EXPORT_INPROGRESS": "2_4_4_3_6_3"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_ACCOUNT_NAME_STRING_IMPORT_INPROGRESS": "3_1_5_1"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_ACCOUNT_KEY_STRING_IMPORT_INPROGRESS": "3_2_5_2"})
    # @mock.patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING_IMPORT_INPROGRESS": "3_3"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING_IMPORT_APPROVED": "3_4"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_ACCOUNT_NAME_STRING_EXPORT_INPROGRESS": "4_1_6_1"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_ACCOUNT_KEY_STRING_EXPORT_INPROGRESS": "4_2_6_2"})
    # @mock.patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING_EXPORT_INPROGRESS": "4_3"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING_EXPORT_APPROVED": "4_4"})
    # @mock.patch.dict(os.environ, {"AZURE_STORAGE_ACCOUNT_NAME_STRING_IMPORT_INPROGRESS": "5_1"})
    # @mock.patch.dict(os.environ, {"AZURE_STORAGE_ACCOUNT_KEY_STRING_IMPORT_INPROGRESS": "5_2"})
    # @mock.patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING_IMPORT_INPROGRESS": "5_3"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING_IMPORT_REJECTED": "5_4"})
    # @mock.patch.dict(os.environ, {"AZURE_STORAGE_ACCOUNT_NAME_STRING_EXPORT_INPROGRESS": "6_1"})
    # @mock.patch.dict(os.environ, {"AZURE_STORAGE_ACCOUNT_KEY_STRING_EXPORT_INPROGRESS": "6_2"})
    # @mock.patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING_EXPORT_INPROGRESS": "6_3"})
    @mock.patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING_EXPORT_REJECTED": "6_4"})
    def test_correct_values_are_returned_when_getting_storage_account_properties(self):
        # Since there are many different properties, make sure we are getting the correct ones
        s_acc_name, s_acc_key, s_conn, d_conn = get_source_dest_env_vars("submitted", "import")
        self.assertEqual(s_acc_name, "1_1")
        self.assertEqual(s_acc_key, "1_2")
        self.assertEqual(s_conn, "1_3")
        self.assertEqual(d_conn, "1_4_3_3_5_3")

        s_acc_name, s_acc_key, s_conn, d_conn = get_source_dest_env_vars("submitted", "export")
        self.assertEqual(s_acc_name, "2_1")
        self.assertEqual(s_acc_key, "2_2")
        self.assertEqual(s_conn, "2_3")
        self.assertEqual(d_conn, "2_4_4_3_6_3")

        s_acc_name, s_acc_key, s_conn, d_conn = get_source_dest_env_vars("approved", "import")
        self.assertEqual(s_acc_name, "3_1_5_1")
        self.assertEqual(s_acc_key, "3_2_5_2")
        self.assertEqual(s_conn, "1_4_3_3_5_3")
        self.assertEqual(d_conn, "3_4")

        s_acc_name, s_acc_key, s_conn, d_conn = get_source_dest_env_vars("approved", "export")
        self.assertEqual(s_acc_name, "4_1_6_1")
        self.assertEqual(s_acc_key, "4_2_6_2")
        self.assertEqual(s_conn, "2_4_4_3_6_3")
        self.assertEqual(d_conn, "4_4")

        s_acc_name, s_acc_key, s_conn, d_conn = get_source_dest_env_vars("rejected", "import")
        self.assertEqual(s_acc_name, "3_1_5_1")
        self.assertEqual(s_acc_key, "3_2_5_2")
        self.assertEqual(s_conn, "1_4_3_3_5_3")
        self.assertEqual(d_conn, "5_4")

        s_acc_name, s_acc_key, s_conn, d_conn = get_source_dest_env_vars("rejected", "export")
        self.assertEqual(s_acc_name, "4_1_6_1")
        self.assertEqual(s_acc_key, "4_2_6_2")
        self.assertEqual(s_conn, "2_4_4_3_6_3")
        self.assertEqual(d_conn, "6_4")
