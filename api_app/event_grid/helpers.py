import asyncio

from azure.core.exceptions import HttpResponseError, ServiceRequestError
from azure.eventgrid import EventGridEvent
from azure.eventgrid.aio import EventGridPublisherClient
from core import credentials
from services.logging import logger

_MAX_RETRIES = 3
_BASE_DELAY_SECONDS = 1.0


def _is_retryable(exc: HttpResponseError) -> bool:
    """Return True for 429 (rate-limited) and any 5xx (server-side) errors."""
    return exc.status_code == 429 or (exc.status_code is not None and exc.status_code >= 500)


async def publish_event(event: EventGridEvent, topic_endpoint: str) -> None:
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            async with credentials.get_credential_async_context() as credential:
                client = EventGridPublisherClient(topic_endpoint, credential)
                async with client:
                    await client.send([event])
            return
        except HttpResponseError as exc:
            if not _is_retryable(exc):
                raise
            last_exc = exc
            logger.warning(
                f"Event Grid publish failed with HTTP {exc.status_code} "
                f"(attempt {attempt + 1}/{_MAX_RETRIES}): {exc}"
            )
        except ServiceRequestError as exc:
            last_exc = exc
            logger.warning(
                f"Event Grid publish failed with a transient network error "
                f"(attempt {attempt + 1}/{_MAX_RETRIES}): {exc}"
            )

        if attempt < _MAX_RETRIES - 1:
            delay = _BASE_DELAY_SECONDS * (2 ** attempt)
            await asyncio.sleep(delay)

    raise last_exc  # type: ignore[misc]
