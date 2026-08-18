import json
from mock import MagicMock, patch

from ScanResultTrigger import main
from shared_code import constants


def _msg(blob_uri, verdict):
    body = json.dumps({"data": {"blobUri": blob_uri, "scanResultType": verdict}})
    m = MagicMock()
    m.get_body.return_value = body.encode("utf-8")
    return m


@patch.dict("os.environ", {"ENABLE_MALWARE_SCANNING": "true"}, clear=True)
@patch("ScanResultTrigger.blob_operations.get_blob_info_from_blob_url")
@patch("shared_code.blob_operations_metadata.merge_container_metadata")
def test_v2_persists_verdict_and_does_not_emit_when_not_submitted(mock_merge, mock_info):
    # v2 core account, request still in Draft (no awaiting flag) -> persist only, no StepResult
    mock_info.return_value = ("stalairlocktre1", "req-1", "f.txt")
    mock_merge.return_value = {constants.METADATA_SCAN_RESULT: constants.NO_THREATS}
    out = MagicMock()

    main(msg=_msg("https://stalairlocktre1.blob.core.windows.net/req-1/f.txt", constants.NO_THREATS), outputEvent=out)

    mock_merge.assert_called_once()
    out.set.assert_not_called()


@patch.dict("os.environ", {"ENABLE_MALWARE_SCANNING": "true"}, clear=True)
@patch("ScanResultTrigger.blob_operations.get_blob_info_from_blob_url")
@patch("shared_code.blob_operations_metadata.merge_container_metadata")
def test_v2_emits_when_already_submitted(mock_merge, mock_info):
    # v2 core account, request already submitted (awaiting flag set) -> emit StepResult
    mock_info.return_value = ("stalairlocktre1", "req-2", "f.txt")
    mock_merge.return_value = {
        constants.METADATA_SCAN_RESULT: constants.NO_THREATS,
        constants.METADATA_AWAITING_SUBMIT: "true",
    }
    out = MagicMock()

    main(msg=_msg("https://stalairlocktre1.blob.core.windows.net/req-2/f.txt", constants.NO_THREATS), outputEvent=out)

    out.set.assert_called_once()


@patch.dict("os.environ", {"ENABLE_MALWARE_SCANNING": "true"}, clear=True)
@patch("ScanResultTrigger.blob_operations.get_blob_info_from_blob_url")
@patch("shared_code.blob_operations_metadata.merge_container_metadata")
def test_v1_emits_step_result_without_persisting(mock_merge, mock_info):
    # v1 legacy in-progress account -> emit StepResult, no metadata persistence
    mock_info.return_value = ("stalimiptre1", "req-3", "f.txt")
    out = MagicMock()

    main(msg=_msg("https://stalimiptre1.blob.core.windows.net/req-3/f.txt", constants.NO_THREATS), outputEvent=out)

    mock_merge.assert_not_called()
    out.set.assert_called_once()
