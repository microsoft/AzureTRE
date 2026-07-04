import json
from mock import MagicMock, patch

import azure.functions as func

from BlobCreatedTrigger import main


def _make_service_bus_message(topic: str, request_id: str, blob_name: str = "test.txt"):
    subject = f"/blobServices/default/containers/{request_id}/blobs/{blob_name}"
    body = json.dumps({"topic": topic, "subject": subject})
    encoded = body.encode("utf-8")
    msg = MagicMock(spec=func.ServiceBusMessage)
    msg.get_body.return_value = encoded
    return msg


class TestV2BlobCreated():

    @patch("BlobCreatedTrigger.get_blob_info_from_topic_and_subject")
    def test_v2_import_approved_does_not_emit_step_result(self, mock_get_blob_info):
        """v2 completion is handled synchronously by StatusChangedQueueTrigger, so
        BlobCreated events from v2 accounts must not emit a StepResult (avoids double completion)."""
        topic = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/stalairlockgtre123"
        request_id = "req-001"
        mock_get_blob_info.return_value = ("stalairlockgtre123", request_id, "test.txt")

        step_result = MagicMock()
        deletion_event = MagicMock()

        msg = _make_service_bus_message(topic, request_id)
        main(msg=msg, stepResultEvent=step_result, dataDeletionEvent=deletion_event)

        step_result.set.assert_not_called()
        deletion_event.set.assert_not_called()

    @patch("BlobCreatedTrigger.get_blob_info_from_topic_and_subject")
    def test_v2_export_approved_does_not_emit_step_result(self, mock_get_blob_info):
        """Core account (v2) BlobCreated events are ignored - completion is signalled synchronously."""
        topic = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/stalairlocktre123"
        request_id = "req-002"
        mock_get_blob_info.return_value = ("stalairlocktre123", request_id, "test.txt")

        step_result = MagicMock()
        deletion_event = MagicMock()

        msg = _make_service_bus_message(topic, request_id)
        main(msg=msg, stepResultEvent=step_result, dataDeletionEvent=deletion_event)

        step_result.set.assert_not_called()
        deletion_event.set.assert_not_called()

    @patch("BlobCreatedTrigger.get_blob_info_from_topic_and_subject")
    def test_v2_non_terminal_stage_does_not_emit_step_result(self, mock_get_blob_info):
        """When a blob is created in a non-terminal stage (e.g., import-external from user upload), skip."""
        topic = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/stalairlocktre123"
        request_id = "req-003"
        mock_get_blob_info.return_value = ("stalairlocktre123", request_id, "test.txt")

        step_result = MagicMock()
        deletion_event = MagicMock()

        msg = _make_service_bus_message(topic, request_id)
        main(msg=msg, stepResultEvent=step_result, dataDeletionEvent=deletion_event)

        step_result.set.assert_not_called()
