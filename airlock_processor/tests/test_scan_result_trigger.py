import json
from unittest.mock import MagicMock, patch

import azure.functions as func

from shared_code import constants
from ScanResultTrigger import main


def _make_message(request_id: str = "req-001", verdict: str = constants.NO_THREATS):
    blob_uri = f"https://stalairlockgtre123.blob.core.windows.net/{request_id}/test.txt"
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
def test_copied_blob_is_suppressed(mock_get_blob_client):
    mock_get_blob_client.return_value = _blob_client({"copied_from": '["container-prev"]'})
    output_event = MagicMock()

    main(msg=_make_message(), outputEvent=output_event)

    output_event.set.assert_not_called()
