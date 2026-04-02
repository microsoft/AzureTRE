import json
import pytest
from mock import MagicMock, patch, call
from unittest.mock import ANY

import azure.functions as func

from shared_code import constants
from BlobCreatedTrigger import main, _handle_v2_blob_created


def _make_service_bus_message(topic: str, request_id: str, blob_name: str = "test.txt"):
    subject = f"/blobServices/default/containers/{request_id}/blobs/{blob_name}"
    body = json.dumps({"topic": topic, "subject": subject})
    encoded = body.encode("utf-8")
    msg = MagicMock(spec=func.ServiceBusMessage)
    msg.get_body.return_value = encoded
    return msg


class TestV2BlobCreated():

    @patch("BlobCreatedTrigger.get_blob_info_from_topic_and_subject")
    @patch("BlobCreatedTrigger.get_container_metadata", create=True)
    def test_v2_import_approved_emits_step_result(self, mock_get_metadata, mock_get_blob_info):
        """When a blob lands in workspace-global with stage=import-approved, emit StepResult approved."""
        topic = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/stalairlockgtre123"
        request_id = "req-001"
        mock_get_blob_info.return_value = ("stalairlockgtre123", request_id, "test.txt")

        step_result = MagicMock()
        deletion_event = MagicMock()

        with patch("BlobCreatedTrigger.get_container_metadata", return_value={"stage": constants.STAGE_IMPORT_APPROVED, "workspace_id": "ws01"}):
            msg = _make_service_bus_message(topic, request_id)
            main(msg=msg, stepResultEvent=step_result, dataDeletionEvent=deletion_event)

        step_result.set.assert_called_once()
        event_data = step_result.set.call_args[0][0]
        assert event_data.data["completed_step"] == constants.STAGE_APPROVAL_INPROGRESS
        assert event_data.data["new_status"] == constants.STAGE_APPROVED

    @patch("BlobCreatedTrigger.get_blob_info_from_topic_and_subject")
    def test_v2_export_approved_emits_step_result(self, mock_get_blob_info):
        """When a blob lands in core with stage=export-approved, emit StepResult approved."""
        topic = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/stalairlocktre123"
        request_id = "req-002"
        mock_get_blob_info.return_value = ("stalairlocktre123", request_id, "test.txt")

        step_result = MagicMock()
        deletion_event = MagicMock()

        with patch("BlobCreatedTrigger.get_container_metadata", return_value={"stage": constants.STAGE_EXPORT_APPROVED, "workspace_id": "ws01"}):
            msg = _make_service_bus_message(topic, request_id)
            main(msg=msg, stepResultEvent=step_result, dataDeletionEvent=deletion_event)

        step_result.set.assert_called_once()
        event_data = step_result.set.call_args[0][0]
        assert event_data.data["completed_step"] == constants.STAGE_APPROVAL_INPROGRESS
        assert event_data.data["new_status"] == constants.STAGE_APPROVED

    @patch("BlobCreatedTrigger.get_blob_info_from_topic_and_subject")
    def test_v2_non_terminal_stage_does_not_emit_step_result(self, mock_get_blob_info):
        """When a blob is created in a non-terminal stage (e.g., import-external from user upload), skip."""
        topic = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/stalairlocktre123"
        request_id = "req-003"
        mock_get_blob_info.return_value = ("stalairlocktre123", request_id, "test.txt")

        step_result = MagicMock()
        deletion_event = MagicMock()

        with patch("BlobCreatedTrigger.get_container_metadata", return_value={"stage": constants.STAGE_IMPORT_EXTERNAL, "workspace_id": "ws01"}):
            msg = _make_service_bus_message(topic, request_id)
            main(msg=msg, stepResultEvent=step_result, dataDeletionEvent=deletion_event)

        step_result.set.assert_not_called()

    @patch("BlobCreatedTrigger.get_blob_info_from_topic_and_subject")
    def test_v2_metadata_read_failure_skips_gracefully(self, mock_get_blob_info):
        """If container metadata can't be read, log warning and return without error."""
        topic = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/stalairlockgtre123"
        request_id = "req-004"
        mock_get_blob_info.return_value = ("stalairlockgtre123", request_id, "test.txt")

        step_result = MagicMock()
        deletion_event = MagicMock()

        with patch("BlobCreatedTrigger.get_container_metadata", side_effect=Exception("not found")):
            msg = _make_service_bus_message(topic, request_id)
            main(msg=msg, stepResultEvent=step_result, dataDeletionEvent=deletion_event)

        step_result.set.assert_not_called()
