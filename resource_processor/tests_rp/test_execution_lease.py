import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.core.exceptions import HttpResponseError, ResourceExistsError, ResourceNotFoundError

from helpers import execution_lease as leases


def http_error(error_type, status_code):
    error = error_type(message=str(status_code))
    error.status_code = status_code
    return error


def container_with(blob):
    container = MagicMock()
    container.get_blob_client.return_value = blob
    container.create_container = AsyncMock()
    return container


@pytest.mark.asyncio
async def test_a_lease_that_another_worker_holds_is_not_acquired():
    blob = MagicMock(upload_blob=AsyncMock(side_effect=http_error(ResourceExistsError, 409)))
    lease = MagicMock(acquire=AsyncMock(side_effect=http_error(HttpResponseError, 409)))
    with patch.object(leases, "BlobLeaseClient", return_value=lease):
        assert await leases.try_acquire(container_with(blob), "resource-1") is None
    lease.acquire.assert_awaited_once_with(lease_duration=leases.LEASE_SECONDS)


@pytest.mark.asyncio
async def test_the_first_lease_creates_the_container_and_the_record():
    blob = MagicMock(upload_blob=AsyncMock(side_effect=[http_error(ResourceNotFoundError, 404), None]))
    container = container_with(blob)
    lease = MagicMock(acquire=AsyncMock())
    with patch.object(leases, "BlobLeaseClient", return_value=lease):
        execution = await leases.try_acquire(container, "resource-1")
    container.get_blob_client.assert_called_once_with("resource-1")
    container.create_container.assert_awaited_once()
    assert blob.upload_blob.await_count == 2
    assert execution.lease is lease


@pytest.mark.asyncio
async def test_another_storage_error_is_raised():
    blob = MagicMock(upload_blob=AsyncMock(side_effect=http_error(HttpResponseError, 403)))
    with pytest.raises(HttpResponseError):
        await leases.try_acquire(container_with(blob), "resource-1")


@pytest.mark.asyncio
async def test_the_worker_waits_for_the_lease_and_releases_it():
    lease = MagicMock(release=AsyncMock())
    execution = leases.ExecutionLease(MagicMock(), lease)
    with (
        patch.object(leases, "try_acquire", AsyncMock(side_effect=[None, None, execution])) as try_acquire,
        patch.object(leases.asyncio, "sleep", AsyncMock()) as sleep,
        patch.object(leases, "keep_renewed", AsyncMock()),
    ):
        async with leases.execution_lease(MagicMock(), "resource-1", lambda: "step") as acquired:
            assert acquired is execution
            lease.release.assert_not_awaited()
    assert try_acquire.await_count == 3
    assert sleep.await_count == 2
    sleep.assert_awaited_with(leases.WAIT_SECONDS)
    lease.release.assert_awaited_once()


@pytest.mark.asyncio
async def test_the_lease_is_released_when_the_step_fails():
    lease = MagicMock(release=AsyncMock())
    execution = leases.ExecutionLease(MagicMock(), lease)
    with (
        patch.object(leases, "try_acquire", AsyncMock(return_value=execution)),
        patch.object(leases, "keep_renewed", AsyncMock()),
        pytest.raises(RuntimeError),
    ):
        async with leases.execution_lease(MagicMock(), "resource-1", lambda: "step"):
            raise RuntimeError("Porter failed")
    lease.release.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content, expected", [(b"", {}), (b"not json", {}), (b"[]", {}), (b'{"stepId": "s"}', {"stepId": "s"})]
)
async def test_a_record_that_is_not_an_object_reads_as_empty(content, expected):
    download = MagicMock(readall=AsyncMock(return_value=content))
    blob = MagicMock(download_blob=AsyncMock(return_value=download), blob_name="resource-1")
    assert await leases.ExecutionLease(blob, MagicMock()).read() == expected


@pytest.mark.asyncio
async def test_a_record_is_written_with_the_lease():
    blob = MagicMock(upload_blob=AsyncMock())
    lease = MagicMock()
    await leases.ExecutionLease(blob, lease).write({"state": "running"})
    blob.upload_blob.assert_awaited_once_with(json.dumps({"state": "running"}), overwrite=True, lease=lease)


def precondition_failed():
    error = HttpResponseError(message="lease lost")
    error.status_code = 412
    return error


@pytest.mark.asyncio
async def test_an_expired_lease_is_taken_again_for_the_record():
    blob = MagicMock(upload_blob=AsyncMock(side_effect=[precondition_failed(), None]))
    lease = MagicMock(acquire=AsyncMock())
    await leases.ExecutionLease(blob, lease).write({"state": "finished"})
    lease.acquire.assert_awaited_once_with(lease_duration=leases.LEASE_SECONDS)
    assert blob.upload_blob.await_count == 2


@pytest.mark.asyncio
async def test_a_lease_that_another_worker_took_stops_the_record_write():
    taken = HttpResponseError(message="lease already present")
    taken.status_code = 409
    blob = MagicMock(upload_blob=AsyncMock(side_effect=[precondition_failed(), None]))
    lease = MagicMock(acquire=AsyncMock(side_effect=taken))
    with pytest.raises(HttpResponseError):
        await leases.ExecutionLease(blob, lease).write({"state": "finished"})
    assert blob.upload_blob.await_count == 1
