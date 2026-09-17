import json
from unittest.mock import MagicMock, patch

import azure.functions as func
from azure.core.exceptions import ResourceNotFoundError

from shared_code import constants
from ScanResultTrigger import main


def _make_message(request_id: str = "req-001", verdict: str = constants.NO_THREATS, container: str = None):
    # The submitted copy uses the request id; the mutable draft upload carries the -draft suffix.
    container = container if container is not None else request_id
    blob_uri = f"https://stalairlockgtre123.blob.core.windows.net/{container}/test.txt"
    body = json.dumps({"data": {"blobUri": blob_uri, "scanResultType": verdict}}).encode("utf-8")
    msg = MagicMock(spec=func.ServiceBusMessage)
    msg.get_body.return_value = body
    return msg


def _blob_client(metadata: dict):
    client = MagicMock()
    client.get_blob_properties.return_value = {"metadata": metadata}
    return client


@patch.dict("os.environ", {"ENABLE_MALWARE_SCANNING": "true"})
@patch("ScanResultTrigger.blob_operations.get_blob_client_from_blob_info")
def test_original_upload_emits_step_result(mock_get_blob_client):
    mock_get_blob_client.return_value = _blob_client({})
    output_event = MagicMock()

    main(msg=_make_message(), outputEvent=output_event)

    output_event.set.assert_called_once()


@patch.dict("os.environ", {"ENABLE_MALWARE_SCANNING": "true"})
@patch("ScanResultTrigger.blob_operations.get_blob_client_from_blob_info")
def test_verdict_is_reported_as_a_fact_not_a_status(mock_get_blob_client):
    mock_get_blob_client.return_value = _blob_client({})
    output_event = MagicMock()

    main(msg=_make_message(), outputEvent=output_event)

    data = output_event.set.call_args.args[0].get_json()
    assert data["scan_result"] == {"clean": True, "message": None}
    assert "new_status" not in data


@patch.dict("os.environ", {"ENABLE_MALWARE_SCANNING": "true"})
@patch("ScanResultTrigger.blob_operations.get_blob_client_from_blob_info")
def test_malicious_verdict_carries_the_reason(mock_get_blob_client):
    mock_get_blob_client.return_value = _blob_client({})
    output_event = MagicMock()

    main(msg=_make_message(verdict="Malicious"), outputEvent=output_event)

    data = output_event.set.call_args.args[0].get_json()
    assert data["scan_result"] == {"clean": False, "message": "Malicious"}


@patch.dict("os.environ", {"ENABLE_MALWARE_SCANNING": "true"})
@patch("ScanResultTrigger.blob_operations.get_blob_client_from_blob_info")
def test_draft_blob_verdict_is_suppressed(mock_get_blob_client):
    mock_get_blob_client.return_value = _blob_client({"copied_from": '["container-prev"]'})
    output_event = MagicMock()

    main(msg=_make_message(container="req-001-draft"), outputEvent=output_event)

    output_event.set.assert_not_called()


@patch.dict("os.environ", {"ENABLE_MALWARE_SCANNING": "true"})
@patch("ScanResultTrigger.blob_operations.get_blob_client_from_blob_info")
def test_submitted_copy_verdict_emitted_without_reading_the_blob(mock_get_blob_client):
    """The verdict gating review must describe the submitted copy, and must not depend on reading it."""
    mock_get_blob_client.side_effect = ResourceNotFoundError("blob unavailable")
    output_event = MagicMock()

    main(msg=_make_message(), outputEvent=output_event)

    output_event.set.assert_called_once()
    mock_get_blob_client.assert_not_called()


@patch.dict("os.environ", {"ENABLE_MALWARE_SCANNING": "true"})
@patch("ScanResultTrigger.blob_operations.get_blob_client_from_blob_info")
def test_v1_copied_blob_still_emits(mock_get_blob_client):
    mock_get_blob_client.return_value = _blob_client({"copied_from": '["container-prev"]'})
    blob_uri = "https://stalimiptre123.blob.core.windows.net/req-001/test.txt"
    body = json.dumps({"data": {"blobUri": blob_uri, "scanResultType": constants.NO_THREATS}}).encode("utf-8")
    msg = MagicMock(spec=func.ServiceBusMessage)
    msg.get_body.return_value = body
    output_event = MagicMock()

    main(msg=msg, outputEvent=output_event)

    output_event.set.assert_called_once()
    mock_get_blob_client.assert_not_called()


@patch.dict("os.environ", {"ENABLE_MALWARE_SCANNING": "true"})
def test_export_draft_on_workspace_global_account_is_suppressed():
    # Export drafts live on the workspace-global account, so suppression must not depend on the account name.
    account = constants.STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE_GLOBAL + "tre123"
    blob_uri = f"https://{account}.blob.core.windows.net/req-001-draft/test.txt"
    body = json.dumps({"data": {"blobUri": blob_uri, "scanResultType": constants.NO_THREATS}}).encode("utf-8")
    msg = MagicMock(spec=func.ServiceBusMessage)
    msg.get_body.return_value = body
    output_event = MagicMock()

    main(msg=msg, outputEvent=output_event)

    output_event.set.assert_not_called()


@patch.dict("os.environ", {"ENABLE_MALWARE_SCANNING": "true"})
def test_export_submitted_copy_on_workspace_global_account_emits():
    account = constants.STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE_GLOBAL + "tre123"
    blob_uri = f"https://{account}.blob.core.windows.net/req-001/test.txt"
    body = json.dumps({"data": {"blobUri": blob_uri, "scanResultType": constants.NO_THREATS}}).encode("utf-8")
    msg = MagicMock(spec=func.ServiceBusMessage)
    msg.get_body.return_value = body
    output_event = MagicMock()

    main(msg=msg, outputEvent=output_event)

    output_event.set.assert_called_once()
