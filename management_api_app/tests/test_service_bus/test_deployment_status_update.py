import json

import pytest
from mock import AsyncMock, patch

from service_bus.deployment_status_update import receive_message_and_update_deployment
from resources import strings

pytestmark = pytest.mark.asyncio


@patch('logging.error')
@patch('service_bus.deployment_status_update.ServiceBusClient')
async def test_receiving_bad_json_logs_error(sb_client, logging_mock):
    payload = "bad"
    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[payload])
    sb_client().get_queue_receiver().complete_message = AsyncMock()

    await receive_message_and_update_deployment()

    logging_mock.assert_called_once_with(strings.DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT)
    sb_client().get_queue_receiver().complete_message.assert_called_once_with(payload)


@patch('service_bus.deployment_status_update.ServiceBusClient')
async def test_receiving_good_message(sb_client):
    message = '{"blah": "blah"}'
    payload = json.loads(message)
    sb_client().get_queue_receiver().receive_messages = AsyncMock(return_value=[payload])
    sb_client().get_queue_receiver().complete_message = AsyncMock()

    await receive_message_and_update_deployment()

    sb_client().get_queue_receiver().complete_message.assert_called_once_with(payload)
