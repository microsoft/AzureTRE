import asyncio
import json
import time
from contextlib import asynccontextmanager, suppress
from typing import Callable, Optional

from azure.core.exceptions import HttpResponseError, ResourceExistsError, ResourceNotFoundError
from azure.storage.blob.aio import BlobLeaseClient, ContainerClient

from helpers.lock_renewal import keep_renewed, stop
from shared.logging import logger

CONTAINER_NAME = "rp-executions"
LEASE_SECONDS = 60
RENEW_SECONDS = 15
WAIT_SECONDS = 30


class ExecutionLease:
    """One worker at a time holds this lease and runs Porter for a resource.

    The blob keeps a small record of the last step that a worker ran for the resource and the results of
    earlier steps, so that a worker that gets the same message again can find the result.
    """

    def __init__(self, blob, lease):
        self.blob = blob
        self.lease = lease
        self.expires = time.monotonic() + LEASE_SECONDS
        # The execution ID in the record that this worker read or wrote last.
        self.execution_id = None

    async def renew(self):
        await self.lease.renew()
        self.expires = time.monotonic() + LEASE_SECONDS

    def seconds_left(self) -> float:
        return self.expires - time.monotonic()

    async def read(self) -> dict:
        record = await self._download()
        self.execution_id = record.get("executionId")
        return record

    async def _download(self) -> dict:
        download = await self.blob.download_blob(lease=self.lease)
        content = await download.readall()
        try:
            record = json.loads(content or b"{}")
        except ValueError:
            # A damaged record does not prove a result, so the worker runs Porter.
            logger.warning(f"Ignoring an invalid execution record in {self.blob.blob_name}")
            return {}
        return record if isinstance(record, dict) else {}

    async def write(self, record: dict):
        try:
            await self.blob.upload_blob(json.dumps(record), overwrite=True, lease=self.lease)
        except HttpResponseError as error:
            if error.status_code != 412:
                raise
            # The lease expired, for example after a storage outage that was longer than the renewal retries.
            # Azure gives the same lease ID again if no other worker took the lease. If one did, this raises 409.
            await self.lease.acquire(lease_duration=LEASE_SECONDS)
            self.expires = time.monotonic() + LEASE_SECONDS
            # Another worker can have taken the lease, written its record and released the lease in the meantime.
            # Keep that record, so that a copy of its message finds the result.
            stored = (await self._download()).get("executionId")
            if stored not in (self.execution_id, record.get("executionId")):
                raise RuntimeError(
                    f"Another worker wrote the execution record {self.blob.blob_name} after the lease expired"
                )
            await self.blob.upload_blob(json.dumps(record), overwrite=True, lease=self.lease)
        self.execution_id = record.get("executionId")


async def create_blob(container: ContainerClient, blob):
    for attempt in (1, 2):
        try:
            await blob.upload_blob(b"{}", overwrite=False)
            return
        except ResourceNotFoundError:
            if attempt == 2:
                raise
            # The first lease in a deployment creates the container.
            with suppress(ResourceExistsError):
                await container.create_container()
        except HttpResponseError as error:
            # The blob exists. With an active lease, Azure can also return 412.
            if error.status_code not in (409, 412):
                raise
            return


async def try_acquire(container: ContainerClient, resource_id: str) -> Optional[ExecutionLease]:
    blob = container.get_blob_client(resource_id)
    await create_blob(container, blob)
    lease = BlobLeaseClient(blob)
    try:
        await lease.acquire(lease_duration=LEASE_SECONDS)
    except HttpResponseError as error:
        if error.status_code == 409:
            return None
        raise
    return ExecutionLease(blob, lease)


@asynccontextmanager
async def execution_lease(container: ContainerClient, resource_id: str, describe: Callable[[], str]):
    """Wait for the lease on this resource, keep it while the caller works, then release it."""
    while (execution := await try_acquire(container, resource_id)) is None:
        # Another worker runs Porter for this resource. Keep the session and wait,
        # so that the steps for the resource stay in order.
        logger.info(f"Waiting for another worker to finish with {describe()}")
        await asyncio.sleep(WAIT_SECONDS)
    renewal = asyncio.create_task(
        keep_renewed("Execution lease", execution.renew, execution.seconds_left, describe, interval=RENEW_SECONDS)
    )
    try:
        yield execution
    finally:
        await stop(renewal)
        try:
            await execution.lease.release()
        except Exception as error:
            # The lease expires by itself after LEASE_SECONDS.
            logger.warning(f"Could not release the execution lease for {describe()}: {error!r}")
