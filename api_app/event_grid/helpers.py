from azure.eventgrid import EventGridEvent
from azure.eventgrid.aio import EventGridPublisherClient
from core import credentials


async def publish_event(event: EventGridEvent, topic_endpoint: str):
    async with credentials.get_credential_async_context() as credential:
        client = EventGridPublisherClient(topic_endpoint, credential)
        async with client:
            await client.send([event])
