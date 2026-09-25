import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from azure.core.exceptions import HttpResponseError, ServiceRequestError
from azure.eventgrid import EventGridEvent

from event_grid.helpers import publish_event


def _make_event():
    return EventGridEvent(
        event_type="test",
        data={"key": "value"},
        subject="test/subject",
        data_version="1.0",
    )


def _http_error(status_code: int) -> HttpResponseError:
    err = HttpResponseError()
    err.status_code = status_code
    return err


@pytest.mark.asyncio
@patch("event_grid.helpers.credentials.get_credential_async_context")
async def test_publish_event_succeeds_on_first_attempt(mock_cred_ctx):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.send = AsyncMock()

    mock_cred = MagicMock()
    mock_cred.__aenter__ = AsyncMock(return_value=mock_cred)
    mock_cred.__aexit__ = AsyncMock(return_value=None)
    mock_cred_ctx.return_value = mock_cred

    with patch("event_grid.helpers.EventGridPublisherClient", return_value=mock_client):
        await publish_event(_make_event(), "https://topic.endpoint")

    mock_client.send.assert_called_once()


@pytest.mark.asyncio
@patch("event_grid.helpers.asyncio.sleep", new_callable=AsyncMock)
@patch("event_grid.helpers.credentials.get_credential_async_context")
async def test_publish_event_retries_on_429_and_succeeds(mock_cred_ctx, mock_sleep):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.send = AsyncMock(side_effect=[_http_error(429), None])

    mock_cred = MagicMock()
    mock_cred.__aenter__ = AsyncMock(return_value=mock_cred)
    mock_cred.__aexit__ = AsyncMock(return_value=None)
    mock_cred_ctx.return_value = mock_cred

    with patch("event_grid.helpers.EventGridPublisherClient", return_value=mock_client):
        await publish_event(_make_event(), "https://topic.endpoint")

    assert mock_client.send.call_count == 2
    mock_sleep.assert_called_once()


@pytest.mark.asyncio
@patch("event_grid.helpers.asyncio.sleep", new_callable=AsyncMock)
@patch("event_grid.helpers.credentials.get_credential_async_context")
async def test_publish_event_retries_on_503_and_succeeds(mock_cred_ctx, mock_sleep):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.send = AsyncMock(side_effect=[_http_error(503), None])

    mock_cred = MagicMock()
    mock_cred.__aenter__ = AsyncMock(return_value=mock_cred)
    mock_cred.__aexit__ = AsyncMock(return_value=None)
    mock_cred_ctx.return_value = mock_cred

    with patch("event_grid.helpers.EventGridPublisherClient", return_value=mock_client):
        await publish_event(_make_event(), "https://topic.endpoint")

    assert mock_client.send.call_count == 2
    mock_sleep.assert_called_once()


@pytest.mark.asyncio
@patch("event_grid.helpers.asyncio.sleep", new_callable=AsyncMock)
@patch("event_grid.helpers.credentials.get_credential_async_context")
async def test_publish_event_retries_on_service_request_error(mock_cred_ctx, mock_sleep):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.send = AsyncMock(side_effect=[ServiceRequestError("network error"), None])

    mock_cred = MagicMock()
    mock_cred.__aenter__ = AsyncMock(return_value=mock_cred)
    mock_cred.__aexit__ = AsyncMock(return_value=None)
    mock_cred_ctx.return_value = mock_cred

    with patch("event_grid.helpers.EventGridPublisherClient", return_value=mock_client):
        await publish_event(_make_event(), "https://topic.endpoint")

    assert mock_client.send.call_count == 2
    mock_sleep.assert_called_once()


@pytest.mark.asyncio
@patch("event_grid.helpers.asyncio.sleep", new_callable=AsyncMock)
@patch("event_grid.helpers.credentials.get_credential_async_context")
async def test_publish_event_raises_after_exhausting_retries(mock_cred_ctx, mock_sleep):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.send = AsyncMock(side_effect=_http_error(429))

    mock_cred = MagicMock()
    mock_cred.__aenter__ = AsyncMock(return_value=mock_cred)
    mock_cred.__aexit__ = AsyncMock(return_value=None)
    mock_cred_ctx.return_value = mock_cred

    with patch("event_grid.helpers.EventGridPublisherClient", return_value=mock_client):
        with pytest.raises(HttpResponseError):
            await publish_event(_make_event(), "https://topic.endpoint")

    assert mock_client.send.call_count == 3  # _MAX_RETRIES
    assert mock_sleep.call_count == 2  # no sleep after last attempt


@pytest.mark.asyncio
@patch("event_grid.helpers.credentials.get_credential_async_context")
async def test_publish_event_does_not_retry_on_non_retryable_http_error(mock_cred_ctx):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.send = AsyncMock(side_effect=_http_error(401))

    mock_cred = MagicMock()
    mock_cred.__aenter__ = AsyncMock(return_value=mock_cred)
    mock_cred.__aexit__ = AsyncMock(return_value=None)
    mock_cred_ctx.return_value = mock_cred

    with patch("event_grid.helpers.EventGridPublisherClient", return_value=mock_client):
        with pytest.raises(HttpResponseError):
            await publish_event(_make_event(), "https://topic.endpoint")

    assert mock_client.send.call_count == 1  # no retries for 401


@pytest.mark.asyncio
@patch("event_grid.helpers.asyncio.sleep", new_callable=AsyncMock)
@patch("event_grid.helpers.credentials.get_credential_async_context")
async def test_publish_event_exponential_backoff_delays(mock_cred_ctx, mock_sleep):
    """Verify delays grow as 1s, 2s (base * 2^attempt)."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.send = AsyncMock(side_effect=_http_error(429))

    mock_cred = MagicMock()
    mock_cred.__aenter__ = AsyncMock(return_value=mock_cred)
    mock_cred.__aexit__ = AsyncMock(return_value=None)
    mock_cred_ctx.return_value = mock_cred

    with patch("event_grid.helpers.EventGridPublisherClient", return_value=mock_client):
        with pytest.raises(HttpResponseError):
            await publish_event(_make_event(), "https://topic.endpoint")

    delays = [call.args[0] for call in mock_sleep.call_args_list]
    assert delays == [1.0, 2.0]
