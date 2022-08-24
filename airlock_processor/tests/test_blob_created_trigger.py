import os
import unittest
from unittest import mock
from unittest.mock import MagicMock, patch
from BlobCreatedTrigger import main
from azure.functions.servicebus import ServiceBusMessage


def _get_blob_client_mock():
    blob_client_mock = MagicMock()
    blob_client_mock.get_blob_properties = MagicMock(return_value={"metadata": {"copied_from": "[\"storage\"]"}})
    return blob_client_mock


def _mock_service_bus_message(body: str):
    encoded_body = str.encode(body, "utf-8")
    message = ServiceBusMessage(body=encoded_body, message_id="123", user_properties={})
    return message


class TestFileEnumeration(unittest.TestCase):

    @patch("BlobCreatedTrigger.get_request_files")
    @patch("BlobCreatedTrigger.get_blob_info_from_topic_and_subject", return_value=(None, None, None))
    @patch("BlobCreatedTrigger.get_blob_client_from_blob_info", return_value=_get_blob_client_mock())
    @mock.patch.dict(os.environ, {"ENABLE_MALWARE_SCANNING": "false"}, clear=True)
    def test_get_request_files_called_during_submit_stage(self, _, __, get_request_files_mock):
        message_body = "{\"topic\":\"\/subscriptions\/<subscription_id>\/resourceGroups\/<resource_group_name>\/providers\/Microsoft.Storage\/storageAccounts\/stalimip\", \"subject\":\"\" }"
        message = _mock_service_bus_message(body=message_body)

        main(msg=message, stepResultEvent=MagicMock(), toDeleteEvent=MagicMock())
        self.assertTrue(get_request_files_mock.called)
