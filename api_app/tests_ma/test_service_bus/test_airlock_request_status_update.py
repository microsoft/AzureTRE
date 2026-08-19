import json
from fastapi import HTTPException, status
import pytest
import time

from mock import AsyncMock, patch
from service_bus.airlock_request_status_update import AirlockStatusUpdater
from db.repositories.airlock_requests import _UNSET
from models.domain.events import AirlockNotificationUserData, AirlockFile
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus, AirlockRequestType
from models.domain.workspace import Workspace
from db.errors import EntityDoesNotExist
from resources import strings

WORKSPACE_ID = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
AIRLOCK_REQUEST_ID = "5dbc15ae-40e1-49a5-834b-595f59d626b7"
EVENT_ID = "0000c8e7-5c42-4fcb-a7fd-294cfc27aa76"
CURRENT_TIME = time.time()


def sample_workspace():
    return Workspace(
        id=WORKSPACE_ID,
        templateName='template name',
        templateVersion='1.0',
        etag='',
        properties={
            "display_name": "research workspace",
            "description": "research workspace",
            "client_id": "12345"
        },
        resourcePath="test")


pytestmark = pytest.mark.asyncio

test_data = [
    'bad',
    '{"good": "json", "bad": "message"}'
]


test_sb_step_result_message = {
    "id": EVENT_ID,
    "subject": "main",
    "data":
    {
        "completed_step": "submitted",
        "new_status": "in_review",
        "request_id": AIRLOCK_REQUEST_ID

    },
    "eventType": "bla",
    "eventTime": "test message",
    "topic": ""
}

test_sb_step_result_message_with_invalid_status = {
    "id": EVENT_ID,
    "subject": "main",
    "data":
    {
        "completed_step": "submitted",
        "new_status": "approved",
        "request_id": AIRLOCK_REQUEST_ID

    },
    "eventType": "bla",
    "eventTime": "test message",
    "topic": ""
}


def sample_airlock_request(status=AirlockRequestStatus.Submitted):
    airlock_request = AirlockRequest(
        id=AIRLOCK_REQUEST_ID,
        workspaceId=WORKSPACE_ID,
        type=AirlockRequestType.Import,
        files=[AirlockFile(
            name="data.txt",
            size=5
        )],
        businessJustification="some test reason",
        status=status,
        createdWhen=CURRENT_TIME,
        createdBy=AirlockNotificationUserData(
            name="John Doe",
            email="john@example.com"
        ),
        updatedWhen=CURRENT_TIME,
        updatedBy=AirlockNotificationUserData(
            name="Test User",
            email="test@user.com"
        )
    )
    return airlock_request


class ServiceBusReceivedMessageMock:
    def __init__(self, message: dict):
        self.message = json.dumps(message)
        self.correlation_id = "test_correlation_id"

    def __str__(self):
        return self.message


@patch("event_grid.helpers.EventGridPublisherClient")
@patch('service_bus.airlock_request_status_update.AirlockRequestRepository.create')
@patch('service_bus.airlock_request_status_update.WorkspaceRepository.create')
@patch('logging.exception')
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_user_emails_by_role_assignment", return_value={"researcher_emails": ["researcher@outlook.com"], "owner_emails": ["owner@outlook.com"]})
async def test_receiving_good_message(_, logging_mock, workspace_repo, airlock_request_repo, eg_client):

    eg_client().send = AsyncMock()
    expected_airlock_request = sample_airlock_request()
    airlock_request_repo.return_value.get_airlock_request_by_id.return_value = expected_airlock_request
    airlock_request_repo.return_value.update_airlock_request.return_value = sample_airlock_request(status=AirlockRequestStatus.InReview)
    workspace_repo.return_value.get_workspace_by_id.return_value = sample_workspace()

    airlockStatusUpdater = AirlockStatusUpdater()
    await airlockStatusUpdater.init_repos()
    complete_message = await airlockStatusUpdater.process_message(ServiceBusReceivedMessageMock(test_sb_step_result_message))

    assert complete_message is True
    airlock_request_repo.return_value.get_airlock_request_by_id.assert_called_once_with(test_sb_step_result_message["data"]["request_id"])
    airlock_request_repo.return_value.update_airlock_request.assert_called_once_with(
        original_request=expected_airlock_request,
        updated_by=expected_airlock_request.updatedBy,
        new_status=test_sb_step_result_message["data"]["new_status"],
        request_files=None,
        status_message=None,
        airlock_review=None,
        review_user_resource=None,
        scan_result=_UNSET)
    assert eg_client().send.call_count == 2
    logging_mock.assert_not_called()


@pytest.mark.parametrize("payload", test_data)
@patch('service_bus.airlock_request_status_update.AirlockRequestRepository.create')
@patch('service_bus.airlock_request_status_update.WorkspaceRepository.create')
@patch('services.logging.logger.exception')
async def test_receiving_bad_json_logs_error(logging_mock, workspace_repo, airlock_request_repo, payload):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(payload)
    airlockStatusUpdater = AirlockStatusUpdater()
    await airlockStatusUpdater.init_repos()
    complete_message = await airlockStatusUpdater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    expected_error_message = f"{strings.STEP_RESULT_MESSAGE_FORMAT_INCORRECT}: {service_bus_received_message_mock.correlation_id}"
    logging_mock.assert_called_once_with(expected_error_message)


@patch('service_bus.airlock_request_status_update.WorkspaceRepository.create')
@patch('service_bus.airlock_request_status_update.AirlockRequestRepository.create')
@patch('services.logging.logger.exception')
@patch('service_bus.airlock_request_status_update.ServiceBusClient')
async def test_updating_non_existent_airlock_request_error_is_logged(sb_client, logging_mock, airlock_request_repo, _):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(test_sb_step_result_message)

    airlock_request_repo.return_value.get_airlock_request_by_id.side_effect = EntityDoesNotExist
    airlockStatusUpdater = AirlockStatusUpdater()
    await airlockStatusUpdater.init_repos()
    complete_message = await airlockStatusUpdater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    expected_error_message = strings.STEP_RESULT_ID_NOT_FOUND.format(test_sb_step_result_message["data"]["request_id"])
    logging_mock.assert_called_once_with(expected_error_message)


@patch('service_bus.airlock_request_status_update.WorkspaceRepository.create')
@patch('service_bus.airlock_request_status_update.AirlockRequestRepository.create')
@patch('services.logging.logger.exception')
async def test_when_updating_and_state_store_exception_error_is_logged(logging_mock, airlock_request_repo, _):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(test_sb_step_result_message)

    airlock_request_repo.return_value.get_airlock_request_by_id.side_effect = Exception
    airlockStatusUpdater = AirlockStatusUpdater()
    await airlockStatusUpdater.init_repos()
    complete_message = await airlockStatusUpdater.process_message(service_bus_received_message_mock)

    assert complete_message is False
    logging_mock.assert_called_once_with("Failed updating request status")


@patch('service_bus.airlock_request_status_update.WorkspaceRepository.create')
@patch('service_bus.airlock_request_status_update.AirlockRequestRepository.create')
@patch('services.logging.logger.error')
async def test_when_updating_and_current_status_differs_from_status_in_state_store_error_is_logged(logging_mock, airlock_request_repo, _):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(test_sb_step_result_message)

    # Not the completed step and not the message's new status, so this is a genuine mismatch rather than a duplicate.
    expected_airlock_request = sample_airlock_request(AirlockRequestStatus.ApprovalInProgress)
    airlock_request_repo.return_value.get_airlock_request_by_id.return_value = expected_airlock_request
    airlockStatusUpdater = AirlockStatusUpdater()
    await airlockStatusUpdater.init_repos()
    complete_message = await airlockStatusUpdater.process_message(service_bus_received_message_mock)

    assert complete_message is False
    expected_error_message = strings.STEP_RESULT_MESSAGE_STATUS_DOES_NOT_MATCH.format(test_sb_step_result_message["data"]["request_id"], test_sb_step_result_message["data"]["completed_step"], expected_airlock_request.status)
    logging_mock.assert_called_once_with(expected_error_message)


test_sb_scan_result_message = {
    "id": EVENT_ID,
    "subject": "main",
    "data": {
        "completed_step": "submitted",
        "request_id": AIRLOCK_REQUEST_ID,
        "scan_result": {"clean": True, "message": None}
    },
    "eventType": "bla",
    "eventTime": "test message",
    "topic": ""
}


@patch('service_bus.airlock_request_status_update.update_and_publish_event_airlock_request')
@patch('service_bus.airlock_request_status_update.WorkspaceRepository.create')
@patch('service_bus.airlock_request_status_update.AirlockRequestRepository.create')
@patch('services.logging.logger.error')
async def test_scan_result_for_draft_request_is_recorded_without_status_change(logging_mock, airlock_request_repo, _, update_and_publish_mock):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(test_sb_scan_result_message)

    expected_airlock_request = sample_airlock_request(AirlockRequestStatus.Draft)
    airlock_request_repo.return_value.get_airlock_request_by_id.return_value = expected_airlock_request
    airlock_request_repo.return_value.update_airlock_request.return_value = expected_airlock_request
    airlockStatusUpdater = AirlockStatusUpdater()
    await airlockStatusUpdater.init_repos()
    complete_message = await airlockStatusUpdater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    airlock_request_repo.return_value.update_airlock_request.assert_called_once_with(
        original_request=expected_airlock_request,
        updated_by=expected_airlock_request.updatedBy,
        scan_result={"clean": True, "message": None})
    update_and_publish_mock.assert_not_called()
    logging_mock.assert_not_called()


@patch('service_bus.airlock_request_status_update.update_and_publish_event_airlock_request')
@patch('service_bus.airlock_request_status_update.WorkspaceRepository.create')
@patch('service_bus.airlock_request_status_update.AirlockRequestRepository.create')
async def test_verdict_arriving_after_file_validation_completes_submission(airlock_request_repo, workspace_repo, update_and_publish_mock):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(test_sb_scan_result_message)

    submitted = sample_airlock_request(AirlockRequestStatus.Submitted)
    scanned = sample_airlock_request(AirlockRequestStatus.Submitted)
    scanned.scanResult = {"clean": True, "message": None}
    airlock_request_repo.return_value.get_airlock_request_by_id.return_value = submitted
    airlock_request_repo.return_value.update_airlock_request.return_value = scanned
    workspace_repo.return_value.get_workspace_by_id.return_value = sample_workspace()

    airlockStatusUpdater = AirlockStatusUpdater()
    await airlockStatusUpdater.init_repos()
    complete_message = await airlockStatusUpdater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    assert update_and_publish_mock.call_args.kwargs["new_status"] == AirlockRequestStatus.InReview


@patch('service_bus.airlock_request_status_update.update_and_publish_event_airlock_request')
@patch('service_bus.airlock_request_status_update.WorkspaceRepository.create')
@patch('service_bus.airlock_request_status_update.AirlockRequestRepository.create')
async def test_file_validation_arriving_after_verdict_completes_submission(airlock_request_repo, workspace_repo, update_and_publish_mock):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(test_sb_step_result_message_with_files)

    scanned = sample_airlock_request(AirlockRequestStatus.Submitted)
    scanned.scanResult = {"clean": True, "message": None}
    airlock_request_repo.return_value.get_airlock_request_by_id.return_value = scanned
    workspace_repo.return_value.get_workspace_by_id.return_value = sample_workspace()
    update_and_publish_mock.return_value = scanned

    airlockStatusUpdater = AirlockStatusUpdater()
    await airlockStatusUpdater.init_repos()
    complete_message = await airlockStatusUpdater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    assert update_and_publish_mock.call_args.kwargs["new_status"] == AirlockRequestStatus.InReview


@patch('service_bus.airlock_request_status_update.update_and_publish_event_airlock_request')
@patch('service_bus.airlock_request_status_update.WorkspaceRepository.create')
@patch('service_bus.airlock_request_status_update.AirlockRequestRepository.create')
async def test_malicious_verdict_blocks_a_validated_submission(airlock_request_repo, workspace_repo, update_and_publish_mock):
    message = json.loads(json.dumps(test_sb_scan_result_message))
    message["data"]["scan_result"] = {"clean": False, "message": "Malicious"}
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(message)

    submitted = sample_airlock_request(AirlockRequestStatus.Submitted)
    scanned = sample_airlock_request(AirlockRequestStatus.Submitted)
    scanned.scanResult = {"clean": False, "message": "Malicious"}
    airlock_request_repo.return_value.get_airlock_request_by_id.return_value = submitted
    airlock_request_repo.return_value.update_airlock_request.return_value = scanned
    workspace_repo.return_value.get_workspace_by_id.return_value = sample_workspace()

    airlockStatusUpdater = AirlockStatusUpdater()
    await airlockStatusUpdater.init_repos()
    complete_message = await airlockStatusUpdater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    assert update_and_publish_mock.call_args.kwargs["new_status"] == AirlockRequestStatus.BlockingInProgress
    assert update_and_publish_mock.call_args.kwargs["status_message"] == "Malicious"


@pytest.mark.parametrize("message", [test_sb_step_result_message, test_sb_scan_result_message])
@pytest.mark.parametrize("final_status", [AirlockRequestStatus.Cancelled, AirlockRequestStatus.Failed, AirlockRequestStatus.Blocked, AirlockRequestStatus.Approved, AirlockRequestStatus.Rejected])
@patch('service_bus.airlock_request_status_update.WorkspaceRepository.create')
@patch('service_bus.airlock_request_status_update.AirlockRequestRepository.create')
@patch('services.logging.logger.error')
async def test_scan_result_for_final_request_is_discarded_not_dead_lettered(logging_mock, airlock_request_repo, _, final_status, message):
    # A late verdict must not mutate a request that has already reached a final state.
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(message)

    expected_airlock_request = sample_airlock_request(final_status)
    airlock_request_repo.return_value.get_airlock_request_by_id.return_value = expected_airlock_request
    airlockStatusUpdater = AirlockStatusUpdater()
    await airlockStatusUpdater.init_repos()
    complete_message = await airlockStatusUpdater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    airlock_request_repo.return_value.update_airlock_request.assert_not_called()
    logging_mock.assert_not_called()


@patch('service_bus.airlock_request_status_update.WorkspaceRepository.create')
@patch('service_bus.airlock_request_status_update.AirlockRequestRepository.create')
@patch('services.logging.logger.exception')
@patch('service_bus.airlock_request_status_update.ServiceBusClient')
async def test_when_updating_and_status_update_is_illegal_error_is_logged(sb_client, logging_mock, airlock_request_repo, _):
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(test_sb_step_result_message_with_invalid_status)

    airlock_request_repo.return_value.get_airlock_request_by_id.side_effect = HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    airlockStatusUpdater = AirlockStatusUpdater()
    await airlockStatusUpdater.init_repos()
    complete_message = await airlockStatusUpdater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    expected_error_message = strings.STEP_RESULT_MESSAGE_INVALID_STATUS.format(test_sb_step_result_message_with_invalid_status["data"]["request_id"], test_sb_step_result_message_with_invalid_status["data"]["completed_step"], test_sb_step_result_message_with_invalid_status["data"]["new_status"])
    logging_mock.assert_called_once_with(expected_error_message)


test_sb_step_result_message_with_files = {
    "id": EVENT_ID,
    "subject": "main",
    "data": {
        "completed_step": "submitted",
        "request_id": AIRLOCK_REQUEST_ID,
        "request_files": [{"name": "test.txt", "size": 5}]
    },
    "eventType": "bla",
    "eventTime": "test message",
    "topic": ""
}


@patch('service_bus.airlock_request_status_update.WorkspaceRepository.create')
@patch('service_bus.airlock_request_status_update.AirlockRequestRepository.create')
@patch('services.logging.logger.error')
async def test_duplicate_step_result_already_applied_is_acknowledged(logging_mock, airlock_request_repo, _):
    # Redelivery of an already-applied result must not be retried until it dead-letters.
    service_bus_received_message_mock = ServiceBusReceivedMessageMock(test_sb_step_result_message)

    already_advanced = sample_airlock_request(AirlockRequestStatus.InReview)
    airlock_request_repo.return_value.get_airlock_request_by_id.return_value = already_advanced
    airlockStatusUpdater = AirlockStatusUpdater()
    await airlockStatusUpdater.init_repos()
    complete_message = await airlockStatusUpdater.process_message(service_bus_received_message_mock)

    assert complete_message is True
    airlock_request_repo.return_value.update_airlock_request.assert_not_called()
    logging_mock.assert_not_called()
