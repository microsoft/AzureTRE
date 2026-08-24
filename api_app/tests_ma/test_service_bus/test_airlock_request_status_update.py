import json
from fastapi import HTTPException, status
import pytest
import time

from mock import AsyncMock, MagicMock, patch
from service_bus.airlock_request_status_update import AirlockStatusUpdater
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


class StopReceiveMessages(BaseException):
    pass


def service_bus_client_context():
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


def credential_context():
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=MagicMock())
    context.__aexit__ = AsyncMock(return_value=False)
    return context


def queue_receiver_context():
    receiver = MagicMock()
    receiver.__aenter__ = AsyncMock(return_value=receiver)
    receiver.__aexit__ = AsyncMock(return_value=False)
    receiver.receive_messages = AsyncMock(return_value=[])
    return receiver


async def run_receive_messages_with_mocks(service_bus_client, time_values, client_side_effect=None):
    updater = AirlockStatusUpdater()
    credential = credential_context()
    receiver = queue_receiver_context()
    service_bus_client.get_queue_receiver.return_value = receiver

    with patch("service_bus.airlock_request_status_update.credentials.get_credential_async_context", return_value=credential), \
            patch("service_bus.airlock_request_status_update.ServiceBusClient", return_value=service_bus_client, side_effect=client_side_effect), \
            patch("service_bus.airlock_request_status_update.time.time", side_effect=time_values), \
            patch("service_bus.airlock_request_status_update.asyncio.sleep", new_callable=AsyncMock):
        await updater.receive_messages()


async def test_receive_messages_reuses_client_for_multiple_polls():
    service_bus_client = service_bus_client_context()
    time_call_count = 0
    client_call_count = 0

    def time_after_two_polls():
        nonlocal time_call_count
        time_call_count += 1
        return 0 if time_call_count <= 5 else 3601

    def create_client(*args, **kwargs):
        nonlocal client_call_count
        client_call_count += 1
        if client_call_count == 1:
            return service_bus_client
        raise StopReceiveMessages()

    with pytest.raises(StopReceiveMessages):
        await run_receive_messages_with_mocks(service_bus_client, time_after_two_polls, create_client)

    assert service_bus_client.get_queue_receiver.call_count == 2
    service_bus_client.__aenter__.assert_awaited_once()
    service_bus_client.__aexit__.assert_awaited_once()


async def test_receive_messages_closes_client_before_hourly_recreation():
    first_client = service_bus_client_context()

    def create_client(*args, **kwargs):
        if create_client.called:
            raise StopReceiveMessages()
        create_client.called = True
        return first_client

    create_client.called = False

    with pytest.raises(StopReceiveMessages):
        with patch("service_bus.airlock_request_status_update.credentials.get_credential_async_context", return_value=credential_context()), \
                patch("service_bus.airlock_request_status_update.ServiceBusClient", side_effect=create_client), \
                patch("service_bus.airlock_request_status_update.time.time", side_effect=[0, 0, 0, 3601]), \
                patch("service_bus.airlock_request_status_update.asyncio.sleep", new_callable=AsyncMock):
            first_client.get_queue_receiver.return_value = queue_receiver_context()
            await AirlockStatusUpdater().receive_messages()

    first_client.__aexit__.assert_awaited_once()
    assert first_client.get_queue_receiver.call_count == 1


async def test_receive_messages_closes_client_after_receiver_failure():
    service_bus_client = service_bus_client_context()
    service_bus_client.get_queue_receiver.side_effect = RuntimeError("receiver failed")
    client_call_count = 0

    def create_client(*args, **kwargs):
        nonlocal client_call_count
        client_call_count += 1
        if client_call_count == 1:
            return service_bus_client
        raise StopReceiveMessages()

    with pytest.raises(StopReceiveMessages):
        await run_receive_messages_with_mocks(service_bus_client, lambda: 0, create_client)

    service_bus_client.__aenter__.assert_awaited_once()
    service_bus_client.__aexit__.assert_awaited_once()


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
        review_user_resource=None)
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

    expected_airlock_request = sample_airlock_request(AirlockRequestStatus.Draft)
    airlock_request_repo.return_value.get_airlock_request_by_id.return_value = expected_airlock_request
    airlockStatusUpdater = AirlockStatusUpdater()
    await airlockStatusUpdater.init_repos()
    complete_message = await airlockStatusUpdater.process_message(service_bus_received_message_mock)

    assert complete_message is False
    expected_error_message = strings.STEP_RESULT_MESSAGE_STATUS_DOES_NOT_MATCH.format(test_sb_step_result_message["data"]["request_id"], test_sb_step_result_message["data"]["completed_step"], expected_airlock_request.status)
    logging_mock.assert_called_once_with(expected_error_message)


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
