from azure.eventgrid import EventGridEvent
from azure.eventgrid.aio import EventGridPublisherClient
from azure.identity.aio import DefaultAzureCredential
from core import config
from contextlib import asynccontextmanager


@asynccontextmanager
async def default_credentials():
    """
    Yields the default credentials.
    """
    credential = DefaultAzureCredential(managed_identity_client_id=config.MANAGED_IDENTITY_CLIENT_ID)
    yield credential
    await credential.close()


async def publish_event(event: EventGridEvent, topic_endpoint: str):
    async with default_credentials() as credential:
        client = EventGridPublisherClient(topic_endpoint, credential)
        async with client:
            await client.send([event])
